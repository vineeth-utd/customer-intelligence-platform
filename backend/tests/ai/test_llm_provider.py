import json
import pytest
import httpx

from app.ai.llm.base import (
    LLMClientError,
    LLMConfigurationError,
    LLMError,
    LLMMessage,
    LLMResponse,
    LLMTransientError,
)
from app.ai.llm.fake import FakeLLMProvider
from app.ai.llm.groq import GroqLLMProvider
from app.ai.llm import get_llm_provider
from app.config.settings import Settings


def test_groq_missing_api_key_raises_configuration_error():
    """Verify that GroqLLMProvider refuses to initialize without an API key."""
    with pytest.raises(LLMConfigurationError, match="Groq API key is required"):
        GroqLLMProvider(api_key=None)

    with pytest.raises(LLMConfigurationError, match="Groq API key is required"):
        GroqLLMProvider(api_key="   ")

    # Factory also fails clearly when Groq is configured without key
    test_settings = Settings(llm_provider="groq", groq_api_key=None)
    with pytest.raises(LLMConfigurationError, match="Groq API key is required"):
        get_llm_provider(test_settings)


def test_get_llm_provider_factory():
    """Verify factory returns appropriate provider based on settings."""
    test_settings_fake = Settings(llm_provider="fake")
    provider = get_llm_provider(test_settings_fake)
    assert isinstance(provider, FakeLLMProvider)

    test_settings_groq = Settings(llm_provider="groq", groq_api_key="test-key-123")
    groq_provider = get_llm_provider(test_settings_groq)
    assert isinstance(groq_provider, GroqLLMProvider)
    assert groq_provider.api_key == "test-key-123"

    test_settings_invalid = Settings(llm_provider="unsupported_provider")
    with pytest.raises(LLMConfigurationError, match="Unsupported llm_provider"):
        get_llm_provider(test_settings_invalid)


@pytest.mark.asyncio
async def test_fake_llm_provider_scripted_responses():
    """Verify FakeLLMProvider returns scripted responses and tracks calls."""
    provider = FakeLLMProvider(
        responses=["Summary response one.", "Summary response two."],
        model="test-fake-model",
    )
    messages = [
        LLMMessage(role="system", content="System instruction"),
        LLMMessage(role="user", content="User facts"),
    ]

    resp1 = await provider.complete(messages, temperature=0.0, max_tokens=256)
    assert resp1.content == "Summary response one."
    assert resp1.model == "test-fake-model"

    resp2 = await provider.complete(messages)
    assert resp2.content == "Summary response two."

    # When exhausted, returns default deterministic text
    resp3 = await provider.complete(messages)
    assert "deterministic test summary" in resp3.content

    assert len(provider.calls) == 3
    assert provider.calls[0]["messages"] == messages
    assert provider.calls[0]["temperature"] == 0.0
    assert provider.calls[0]["max_tokens"] == 256


@pytest.mark.asyncio
async def test_fake_llm_provider_configurable_failures():
    """Verify FakeLLMProvider raises configured exceptions in sequence."""
    provider = FakeLLMProvider(
        responses=["Success after error."],
        failures=[LLMTransientError("Simulated rate limit")],
    )
    messages = [LLMMessage(role="user", content="Hello")]

    with pytest.raises(LLMTransientError, match="Simulated rate limit"):
        await provider.complete(messages)

    # Next attempt succeeds
    resp = await provider.complete(messages)
    assert resp.content == "Success after error."


@pytest.mark.asyncio
async def test_groq_payload_and_header_construction():
    """Verify GroqLLMProvider constructs correct headers, body, and parses response."""
    captured_request = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            status_code=200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "model": "llama-3.3-70b-versatile",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "This is a valid test summary of the facts.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 120, "completion_tokens": 45},
            },
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GroqLLMProvider(
        api_key="gsk_test_secret_123",
        model="llama-3.3-70b-versatile",
        client=mock_client,
    )

    messages = [
        LLMMessage(role="system", content="Be concise."),
        LLMMessage(role="user", content="Revenue is 100."),
    ]
    resp = await provider.complete(messages, temperature=0.0, max_tokens=512)

    assert resp.content == "This is a valid test summary of the facts."
    assert resp.model == "llama-3.3-70b-versatile"
    assert resp.prompt_tokens == 120
    assert resp.completion_tokens == 45

    assert captured_request is not None
    assert captured_request.url == "https://api.groq.com/openai/v1/chat/completions"
    assert captured_request.headers["Authorization"] == "Bearer gsk_test_secret_123"
    assert captured_request.headers["Content-Type"] == "application/json"

    body = json.loads(captured_request.content.decode("utf-8"))
    assert body["model"] == "llama-3.3-70b-versatile"
    assert body["temperature"] == 0.0
    assert body["max_tokens"] == 512
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "system"


@pytest.mark.asyncio
async def test_groq_transient_retry_handling():
    """Verify GroqLLMProvider retries on transient errors (429/5xx) and succeeds."""
    attempt_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            return httpx.Response(status_code=429, text="Rate limit exceeded")
        return httpx.Response(
            status_code=200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "Summary after retry."}}
                ],
                "model": "llama-3.3-70b-versatile",
            },
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GroqLLMProvider(
        api_key="gsk_test",
        initial_delay_seconds=0.01,
        max_retries=2,
        client=mock_client,
    )

    resp = await provider.complete([LLMMessage(role="user", content="facts")])
    assert resp.content == "Summary after retry."
    assert attempt_count == 2


@pytest.mark.asyncio
async def test_groq_transient_retry_exhaustion_raises():
    """Verify GroqLLMProvider raises LLMTransientError when retries are exhausted."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=503, text="Service Unavailable")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GroqLLMProvider(
        api_key="gsk_test",
        initial_delay_seconds=0.01,
        max_retries=2,
        client=mock_client,
    )

    with pytest.raises(LLMTransientError, match="status 503 after 3 attempts"):
        await provider.complete([LLMMessage(role="user", content="facts")])


@pytest.mark.asyncio
async def test_groq_client_error_fails_fast_without_retry():
    """Verify GroqLLMProvider raises LLMClientError immediately without retrying on 401."""
    attempt_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt_count
        attempt_count += 1
        return httpx.Response(status_code=401, text="Invalid API Key")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GroqLLMProvider(
        api_key="gsk_bad",
        initial_delay_seconds=0.01,
        max_retries=3,
        client=mock_client,
    )

    with pytest.raises(LLMClientError, match="non-retryable status 401"):
        await provider.complete([LLMMessage(role="user", content="facts")])

    assert attempt_count == 1  # No retries for 401
