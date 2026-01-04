"""Application settings."""

from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    """Application configuration settings."""

    # Catalog API settings (Phase 3.5)
    catalog_api_url: Optional[str] = None

    # CSV settings
    csv_path: Optional[str] = None

    # Retrieval settings
    top_k: int = 5
    max_revisions: int = 2

    # Logging
    verbose: bool = False
