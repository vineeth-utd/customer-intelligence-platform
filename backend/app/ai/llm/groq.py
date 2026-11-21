import asyncio
import logging
from typing import Optional

import httpx

from app.ai.llm.base import (
    LLMClientError,
    LLMConfigurationError,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMTransientError,
)

logger = logging.getLogger(__name__)


class GroqLLMProvider(LLMProvider):
    """
    Groq LLM provider implementation communicating via OpenAI-compatible HTTP chat completions API.
    Handles bounded infrastructure retries for transient errors (429, 5xx, timeouts).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        base_url: str = "https://api.groq.com/openai/v1",
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        initial_delay_seconds: float = 0.5,
        backoff_factor: float = 2.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        if not api_key or not api_key.strip():
            raise LLMConfigurationError(
                "Groq API key is required. Set GROQ_API_KEY environment variable or settings.groq_api_key."
            )
        self.api_key = api_key.strip()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.initial_delay_seconds = initial_delay_seconds
        self.backoff_factor = backoff_factor
        self._client = client

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        attempts = 0
        current_delay = self.initial_delay_seconds

        while True:
            attempts += 1
            try:
                if self._client is not None:
                    response = await self._client.post(
                        url, json=payload, headers=headers, timeout=self.timeout_seconds
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                        response = await client.post(url, json=payload, headers=headers)

                if response.status_code >= 400:
                    response.raise_for_status()

                data = response.json()
                choice = data["choices"][0]
                content = choice["message"]["content"]
                usage = data.get("usage", {})
                return LLMResponse(
                    content=content,
                    model=data.get("model", self.model),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                )

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code in (429, 500, 502, 503, 504):
                    if attempts > self.max_retries:
                        raise LLMTransientError(
                            f"Groq request failed with status {status_code} after {attempts} attempts: {exc.response.text}"
                        ) from exc

                    logger.warning(
                        "Transient Groq error %s on attempt %s/%s. Retrying in %.2fs...",
                        status_code,
                        attempts,
                        self.max_retries,
                        current_delay,
                    )
                    retry_after = exc.response.headers.get("Retry-After")
                    sleep_time = (
                        float(retry_after)
                        if retry_after and retry_after.isdigit()
                        else current_delay
                    )
                    await asyncio.sleep(sleep_time)
                    current_delay *= self.backoff_factor

                elif status_code in (400, 401, 403, 404):
                    raise LLMClientError(
                        f"Groq request failed with non-retryable status {status_code}: {exc.response.text}"
                    ) from exc
                else:
                    raise LLMError(
                        f"Groq request failed with unexpected status {status_code}: {exc.response.text}"
                    ) from exc

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempts > self.max_retries:
                    raise LLMTransientError(
                        f"Groq request failed after {attempts} attempts due to network/timeout error: {exc}"
                    ) from exc

                logger.warning(
                    "Network/timeout error on attempt %s/%s (%s). Retrying in %.2fs...",
                    attempts,
                    self.max_retries,
                    exc,
                    current_delay,
                )
                await asyncio.sleep(current_delay)
                current_delay *= self.backoff_factor
