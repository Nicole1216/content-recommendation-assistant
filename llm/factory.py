"""LLM client factory."""

from enum import Enum
from typing import Optional

from .base_client import BaseLLMClient
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


def create_llm_client(
    provider: LLMProvider,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> BaseLLMClient:
    """
    Create an LLM client for the specified provider.

    Args:
        provider: LLM provider (openai or anthropic)
        api_key: API key for the provider
        model: Optional model override

    Returns:
        Configured LLM client

    Raises:
        ValueError: If provider is not supported
    """
    if provider == LLMProvider.OPENAI:
        return OpenAIClient(api_key=api_key, model=model)
    elif provider == LLMProvider.ANTHROPIC:
        return AnthropicClient(api_key=api_key, model=model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
