"""Application settings."""

import os
from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    """Application configuration settings."""

    # CSV data source (required)
    csv_path: str = "data/Udacity_Content_Catalog_Skill.csv"

    # LLM Provider settings
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_model: Optional[str] = None  # Override default model (gpt-5.2 or claude-sonnet-4)

    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Memory settings
    memory_enabled: bool = True
    db_path: str = "data/conversations.db"

    # ReAct settings
    react_enabled: bool = True
    max_react_iterations: int = 3  # Reduced from 5 for faster responses

    # Retrieval settings
    top_k: int = 5
    max_revisions: int = 1  # Reduced from 2 for faster responses

    # Logging
    verbose: bool = False

    def __init__(self, **data):
        # Auto-load API keys from environment if not provided
        if "openai_api_key" not in data or data["openai_api_key"] is None:
            data["openai_api_key"] = os.environ.get("OPENAI_API_KEY")

        if "anthropic_api_key" not in data or data["anthropic_api_key"] is None:
            data["anthropic_api_key"] = os.environ.get("ANTHROPIC_API_KEY")

        super().__init__(**data)

    def get_llm_api_key(self) -> Optional[str]:
        """Get the API key for the configured LLM provider."""
        if self.llm_provider == "openai":
            return self.openai_api_key
        elif self.llm_provider == "anthropic":
            return self.anthropic_api_key
        return None
