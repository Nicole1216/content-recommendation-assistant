"""Application settings."""

from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    """Application configuration settings."""

    # CSV data source (required)
    csv_path: str = "data/NLC_Skill_Data.csv"

    # Retrieval settings
    top_k: int = 5
    max_revisions: int = 2

    # Logging
    verbose: bool = False
