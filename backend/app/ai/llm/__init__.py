from typing import Optional

from app.ai.llm.base import (
    LLMClientError,
    LLMConfigurationError,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMTransientError,
)
from app.ai.llm.fake import FakeLLMProvider
from app.ai.llm.groq import GroqLLMProvider
from app.config.settings import Settings, settings as global_settings


def get_llm_provider(settings: Optional[Settings] = None) -> LLMProvider:
    """
    Factory for instantiating the configured LLM provider.
    Fails clearly with LLMConfigurationError if required credentials for the configured
    provider are missing. Never silently falls back to a fake provider.
    """
    active_settings = settings or global_settings
    provider_name = active_settings.llm_provider.lower().strip()

    if provider_name == "groq":
        return GroqLLMProvider(
            api_key=active_settings.groq_api_key,
            model=active_settings.groq_model,
            base_url=active_settings.groq_base_url,
            timeout_seconds=active_settings.llm_request_timeout_seconds,
            max_retries=active_settings.llm_max_retries,
            initial_delay_seconds=active_settings.llm_retry_initial_delay_seconds,
            backoff_factor=active_settings.llm_retry_backoff_factor,
        )
    elif provider_name == "fake":
        return FakeLLMProvider()
    else:
        raise LLMConfigurationError(
            f"Unsupported llm_provider: '{active_settings.llm_provider}'. Supported: 'groq', 'fake'."
        )


__all__ = [
    "FakeLLMProvider",
    "GroqLLMProvider",
    "LLMClientError",
    "LLMConfigurationError",
    "LLMError",
    "LLMMessage",
    "LLMProvider",
    "LLMResponse",
    "LLMTransientError",
    "get_llm_provider",
]
