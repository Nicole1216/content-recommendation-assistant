"""SQLite-based memory store for conversation persistence."""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from .models import Conversation, ConversationTurn, ConversationSummary

logger = logging.getLogger(__name__)


class SQLiteMemoryStore:
    """SQLite-based persistent memory store."""

    def __init__(self, db_path: str = "data/conversations.db"):
        """
        Initialize SQLite memory store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                company_name TEXT,
                persona TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Turns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                turn_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)

        # Summaries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                conversation_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                key_topics TEXT,
                turn_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)

        # Indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_turns_conversation ON turns(conversation_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_company ON conversations(company_name)"
        )

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def create_conversation(
        self,
        conversation_id: str,
        company_name: Optional[str],
        persona: str
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            conversation_id: Unique conversation ID
            company_name: Optional company name
            persona: Audience persona (CTO, HR, L&D)

        Returns:
            Created Conversation object
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now()

        cursor.execute(
            """
            INSERT INTO conversations (conversation_id, company_name, persona, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, company_name, persona, now, now)
        )

        conn.commit()
        conn.close()

        return Conversation(
            conversation_id=conversation_id,
            company_name=company_name,
            persona=persona,
            created_at=now,
            updated_at=now,
            turns=[]
        )

    def add_turn(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> ConversationTurn:
        """
        Add a turn to a conversation.

        Args:
            conversation_id: Conversation ID
            role: Role (user, assistant, system)
            content: Message content
            metadata: Optional metadata (tool calls, citations)

        Returns:
            Created ConversationTurn object
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get next turn_id
        cursor.execute(
            "SELECT MAX(turn_id) FROM turns WHERE conversation_id = ?",
            (conversation_id,)
        )
        result = cursor.fetchone()
        turn_id = (result[0] or 0) + 1

        now = datetime.now()
        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute(
            """
            INSERT INTO turns (conversation_id, turn_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, turn_id, role, content, now, metadata_json)
        )

        # Update conversation timestamp
        cursor.execute(
            "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
            (now, conversation_id)
        )

        conn.commit()
        conn.close()

        return ConversationTurn(
            turn_id=turn_id,
            role=role,
            content=content,
            timestamp=now,
            metadata=metadata
        )

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get a conversation with all turns.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation object or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get conversation
        cursor.execute(
            "SELECT * FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        )
        conv_row = cursor.fetchone()

        if not conv_row:
            conn.close()
            return None

        # Get turns
        cursor.execute(
            """
            SELECT turn_id, role, content, timestamp, metadata
            FROM turns
            WHERE conversation_id = ?
            ORDER BY turn_id
            """,
            (conversation_id,)
        )
        turn_rows = cursor.fetchall()
        conn.close()

        turns = []
        for row in turn_rows:
            metadata = json.loads(row["metadata"]) if row["metadata"] else None
            turns.append(ConversationTurn(
                turn_id=row["turn_id"],
                role=row["role"],
                content=row["content"],
                timestamp=datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else datetime.now(),
                metadata=metadata
            ))

        return Conversation(
            conversation_id=conv_row["conversation_id"],
            company_name=conv_row["company_name"],
            persona=conv_row["persona"],
            created_at=datetime.fromisoformat(conv_row["created_at"]) if conv_row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(conv_row["updated_at"]) if conv_row["updated_at"] else datetime.now(),
            turns=turns
        )

    def get_recent_turns(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[ConversationTurn]:
        """
        Get most recent turns from a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of turns to return

        Returns:
            List of recent ConversationTurn objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT turn_id, role, content, timestamp, metadata
            FROM turns
            WHERE conversation_id = ?
            ORDER BY turn_id DESC
            LIMIT ?
            """,
            (conversation_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()

        turns = []
        for row in reversed(rows):  # Reverse to get chronological order
            metadata = json.loads(row["metadata"]) if row["metadata"] else None
            turns.append(ConversationTurn(
                turn_id=row["turn_id"],
                role=row["role"],
                content=row["content"],
                timestamp=datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else datetime.now(),
                metadata=metadata
            ))

        return turns

    def update_summary(
        self,
        conversation_id: str,
        summary: str,
        key_topics: List[str],
        turn_count: int
    ):
        """
        Update or create conversation summary.

        Args:
            conversation_id: Conversation ID
            summary: Summary text
            key_topics: List of key topics
            turn_count: Number of turns summarized
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now()
        topics_json = json.dumps(key_topics)

        cursor.execute(
            """
            INSERT OR REPLACE INTO summaries
            (conversation_id, summary, key_topics, turn_count, last_updated)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, summary, topics_json, turn_count, now)
        )

        conn.commit()
        conn.close()

    def get_summary(self, conversation_id: str) -> Optional[ConversationSummary]:
        """
        Get conversation summary.

        Args:
            conversation_id: Conversation ID

        Returns:
            ConversationSummary or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM summaries WHERE conversation_id = ?",
            (conversation_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return ConversationSummary(
            conversation_id=row["conversation_id"],
            summary=row["summary"],
            key_topics=json.loads(row["key_topics"]) if row["key_topics"] else [],
            turn_count=row["turn_count"],
            last_updated=datetime.fromisoformat(row["last_updated"]) if row["last_updated"] else datetime.now()
        )

    def get_turn_count(self, conversation_id: str) -> int:
        """
        Get the number of turns in a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Number of turns
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM turns WHERE conversation_id = ?",
            (conversation_id,)
        )
        result = cursor.fetchone()
        conn.close()

        return result[0] if result else 0

    def list_conversations(
        self,
        company_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Conversation]:
        """
        List conversations, optionally filtered by company.

        Args:
            company_name: Optional company name filter
            limit: Maximum number of conversations

        Returns:
            List of Conversation objects (without turns)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if company_name:
            cursor.execute(
                """
                SELECT * FROM conversations
                WHERE company_name = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (company_name, limit)
            )
        else:
            cursor.execute(
                """
                SELECT * FROM conversations
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,)
            )

        rows = cursor.fetchall()
        conn.close()

        conversations = []
        for row in rows:
            conversations.append(Conversation(
                conversation_id=row["conversation_id"],
                company_name=row["company_name"],
                persona=row["persona"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
                turns=[]  # Don't load turns for listing
            ))

        return conversations
