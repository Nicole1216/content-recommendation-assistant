"""Application settings."""

import os
from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    """Application configuration settings."""

    # CSV data source (for local fallback)
    csv_path: str = "data/Udacity_Content_Catalog_Skill.csv"

    # LLM Provider settings
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_model: Optional[str] = None  # Override default model (gpt-5.2 or claude-sonnet-4)

    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Azure AI Search settings
    azure_search_endpoint: Optional[str] = None
    azure_search_api_key: Optional[str] = None
    azure_search_index: str = "udacity-programs"
    use_azure_search: bool = True  # Use Azure Search if configured, else local

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

        # Auto-load Azure Search settings from environment
        if "azure_search_endpoint" not in data or data["azure_search_endpoint"] is None:
            data["azure_search_endpoint"] = os.environ.get("AZURE_SEARCH_ENDPOINT")

        if "azure_search_api_key" not in data or data["azure_search_api_key"] is None:
            data["azure_search_api_key"] = os.environ.get("AZURE_SEARCH_API_KEY")

        super().__init__(**data)

    def is_azure_search_configured(self) -> bool:
        """Check if Azure Search is configured."""
        return bool(self.azure_search_endpoint and self.azure_search_api_key)

    def get_llm_api_key(self) -> Optional[str]:
        """Get the API key for the configured LLM provider."""
        if self.llm_provider == "openai":
            return self.openai_api_key
        elif self.llm_provider == "anthropic":
            return self.anthropic_api_key
        return None
