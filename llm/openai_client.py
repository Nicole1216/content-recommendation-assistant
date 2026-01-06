"""OpenAI LLM client implementation."""

import os
import json
import logging
from typing import Optional, List, Dict, Any

from .base_client import BaseLLMClient, Message, LLMResponse, ToolCall

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client implementation."""

    DEFAULT_MODEL = "gpt-5.2"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
            model: Model to use (default: gpt-5.2)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or self.DEFAULT_MODEL
        self.client = None

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"OpenAI client initialized with model: {self.model}")
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
        else:
            logger.warning("No OpenAI API key provided")

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """Send chat completion request to OpenAI."""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized. Check API key.")

        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_msg = {"role": msg.role, "content": msg.content}
            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id
            # Include tool_calls for assistant messages that made tool calls
            if msg.tool_calls:
                openai_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in msg.tool_calls
                ]
            openai_messages.append(openai_msg)

        # Build request kwargs
        kwargs = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,  # GPT-5.2 uses max_completion_tokens
        }

        # Add tools if provided
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**kwargs)

            # Extract content
            choice = response.choices[0]
            content = choice.message.content or ""

            # Extract tool calls if present
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = []
                for tc in choice.message.tool_calls:
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments)
                    ))

            # Extract usage
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                finish_reason=choice.finish_reason
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "openai"

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model
