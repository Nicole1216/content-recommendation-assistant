"""Anthropic Claude LLM client implementation."""

import os
import json
import logging
from typing import Optional, List, Dict, Any

from .base_client import BaseLLMClient, Message, LLMResponse, ToolCall

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client implementation."""

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
            model: Model to use (default: claude-sonnet-4-20250514)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model or self.DEFAULT_MODEL
        self.client = None

        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"Anthropic client initialized with model: {self.model}")
            except ImportError:
                logger.error("anthropic package not installed. Run: pip install anthropic")
        else:
            logger.warning("No Anthropic API key provided")

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """Send chat completion request to Anthropic."""
        if not self.client:
            raise RuntimeError("Anthropic client not initialized. Check API key.")

        # Separate system message from conversation
        system_content = ""
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                system_content += msg.content + "\n"
            elif msg.role == "tool":
                # Convert tool response to user message with tool_result
                conversation_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content
                    }]
                })
            elif msg.role == "assistant" and msg.tool_calls:
                # Assistant message with tool calls - format as content blocks
                content_blocks = []
                if msg.content:
                    content_blocks.append({
                        "type": "text",
                        "text": msg.content
                    })
                for tc in msg.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments
                    })
                conversation_messages.append({
                    "role": "assistant",
                    "content": content_blocks
                })
            else:
                conversation_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Build request kwargs
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": conversation_messages,
        }

        if system_content:
            kwargs["system"] = system_content.strip()

        # Convert tools to Anthropic format
        if tools:
            anthropic_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool["function"]
                    anthropic_tools.append({
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {})
                    })
            if anthropic_tools:
                kwargs["tools"] = anthropic_tools

        try:
            response = self.client.messages.create(**kwargs)

            # Extract content and tool calls
            content = ""
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input
                    ))

            # Extract usage
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }

            return LLMResponse(
                content=content,
                tool_calls=tool_calls if tool_calls else None,
                usage=usage,
                finish_reason=response.stop_reason
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "anthropic"

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model
