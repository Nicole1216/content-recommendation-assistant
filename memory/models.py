"""Memory data models."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """A single turn in a conversation."""
    turn_id: int
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None  # For tool calls, citations, etc.


class Conversation(BaseModel):
    """A complete conversation."""
    conversation_id: str
    company_name: Optional[str] = None
    persona: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    turns: List[ConversationTurn] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    """Summary of a conversation for context compression."""
    conversation_id: str
    summary: str
    key_topics: List[str] = Field(default_factory=list)
    turn_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)
