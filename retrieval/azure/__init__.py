"""Azure AI Search integration."""

from .search_client import AzureSearchClient
from .index_schema import create_index_schema

__all__ = ["AzureSearchClient", "create_index_schema"]
