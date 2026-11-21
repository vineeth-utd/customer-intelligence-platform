from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LLMError(Exception):
    """Base exception for all LLM provider errors."""
    pass


class LLMConfigurationError(LLMError):
    """Raised when an LLM provider is misconfigured or missing required credentials."""
    pass


class LLMClientError(LLMError):
    """Raised on non-retryable client errors (e.g. 400 Bad Request, 401 Unauthorized, 403 Forbidden)."""
    pass


class LLMTransientError(LLMError):
    """Raised on retryable transient errors (e.g. 429 Rate Limit, 5xx Server Error, network timeout)."""
    pass


class LLMMessage(BaseModel):
    """Represents a role-based message in a chat completion conversation."""
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant"]
    content: str


class LLMResponse(BaseModel):
    """Standardized response from an LLM provider."""
    model_config = ConfigDict(extra="forbid")

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMProvider(ABC):
    """Abstract interface for low-level LLM providers."""

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> LLMResponse:
        """
        Execute a chat completion request with bounded parameters.
        Must handle its own infrastructure retries for transient errors.
        """
        pass
