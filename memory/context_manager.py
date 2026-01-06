"""Conversation context manager for LLM context window management."""

import logging
from typing import List, Optional

from .sqlite_store import SQLiteMemoryStore
from .models import ConversationTurn
from llm.base_client import BaseLLMClient, Message

logger = logging.getLogger(__name__)


class ConversationContextManager:
    """Manages conversation context for LLM calls."""

    # Configuration
    MAX_CONTEXT_TURNS = 10  # Maximum turns to include in context
    SUMMARIZE_AFTER_TURNS = 20  # Summarize after this many turns

    def __init__(
        self,
        store: SQLiteMemoryStore,
        llm_client: Optional[BaseLLMClient] = None
    ):
        """
        Initialize context manager.

        Args:
            store: SQLite memory store
            llm_client: Optional LLM client for summarization
        """
        self.store = store
        self.llm_client = llm_client

    def get_context_messages(self, conversation_id: str) -> List[Message]:
        """
        Get messages for LLM context window.

        Includes summary (if available) plus recent turns.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of Message objects for LLM context
        """
        messages = []

        # Get summary if available
        summary = self.store.get_summary(conversation_id)
        if summary:
            messages.append(Message(
                role="system",
                content=f"Previous conversation summary: {summary.summary}\nKey topics discussed: {', '.join(summary.key_topics)}"
            ))

        # Get recent turns
        turns = self.store.get_recent_turns(
            conversation_id,
            limit=self.MAX_CONTEXT_TURNS
        )

        for turn in turns:
            messages.append(Message(
                role=turn.role,
                content=turn.content
            ))

        return messages

    def maybe_summarize(self, conversation_id: str):
        """
        Summarize conversation if it's getting long.

        Uses LLM to generate summary of older turns.

        Args:
            conversation_id: Conversation ID
        """
        turn_count = self.store.get_turn_count(conversation_id)

        # Check if we need to summarize
        if turn_count < self.SUMMARIZE_AFTER_TURNS:
            return

        # Check if we already have a recent summary
        existing_summary = self.store.get_summary(conversation_id)
        if existing_summary and existing_summary.turn_count >= turn_count - 5:
            # Summary is recent enough
            return

        if self.llm_client:
            self._generate_summary(conversation_id, turn_count)
        else:
            logger.warning("No LLM client available for summarization")

    def _generate_summary(self, conversation_id: str, turn_count: int):
        """
        Use LLM to generate conversation summary.

        Args:
            conversation_id: Conversation ID
            turn_count: Current turn count
        """
        try:
            # Get all turns for summarization
            conversation = self.store.get_conversation(conversation_id)
            if not conversation:
                return

            # Build conversation text
            turns_text = "\n".join([
                f"{turn.role.upper()}: {turn.content}"
                for turn in conversation.turns
            ])

            # Generate summary using LLM
            messages = [
                Message(
                    role="system",
                    content="""You are a conversation summarizer. Create a concise summary of the conversation below.

Output format:
SUMMARY: [2-3 sentence summary of what was discussed and decided]
KEY_TOPICS: [comma-separated list of main topics]"""
                ),
                Message(
                    role="user",
                    content=f"Summarize this conversation:\n\n{turns_text}"
                )
            ]

            response = self.llm_client.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )

            # Parse response
            content = response.content
            summary = ""
            key_topics = []

            for line in content.split("\n"):
                if line.startswith("SUMMARY:"):
                    summary = line[8:].strip()
                elif line.startswith("KEY_TOPICS:"):
                    topics_str = line[11:].strip()
                    key_topics = [t.strip() for t in topics_str.split(",")]

            if summary:
                self.store.update_summary(
                    conversation_id=conversation_id,
                    summary=summary,
                    key_topics=key_topics,
                    turn_count=turn_count
                )
                logger.info(f"Generated summary for conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")

    def get_conversation_context_string(self, conversation_id: str) -> str:
        """
        Get conversation context as a single string.

        Useful for including in system prompts.

        Args:
            conversation_id: Conversation ID

        Returns:
            Formatted context string
        """
        messages = self.get_context_messages(conversation_id)

        if not messages:
            return ""

        parts = ["=== Previous Conversation ==="]
        for msg in messages:
            if msg.role == "system":
                parts.append(f"[Context]: {msg.content}")
            else:
                parts.append(f"{msg.role.upper()}: {msg.content}")
        parts.append("=== End Previous Conversation ===")

        return "\n".join(parts)
