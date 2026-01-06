"""Base LLM client interface."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ToolCall(BaseModel):
    """Tool call from LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


class Message(BaseModel):
    """Chat message."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: Optional[str] = None  # For tool responses
    tool_calls: Optional[List["ToolCall"]] = None  # For assistant messages with tool calls


class LLMResponse(BaseModel):
    """Response from LLM."""
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """
        Send chat completion request.

        Args:
            messages: List of messages in conversation
            tools: Optional list of tool definitions for function calling
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with content and optional tool calls
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the LLM provider."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the name of the model being used."""
        pass
