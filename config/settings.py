"""Application settings."""

import os
from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    """Application configuration settings."""

    # CSV data source (required)
    csv_path: str = "data/NLC_Skill_Data.csv"

    # OpenAI API key for embeddings (optional - falls back to keyword search if not provided)
    openai_api_key: Optional[str] = None

    # Retrieval settings
    top_k: int = 5
    max_revisions: int = 2

    # Logging
    verbose: bool = False

    def __init__(self, **data):
        # Auto-load OpenAI API key from environment if not provided
        if "openai_api_key" not in data or data["openai_api_key"] is None:
            data["openai_api_key"] = os.environ.get("OPENAI_API_KEY")
        super().__init__(**data)
