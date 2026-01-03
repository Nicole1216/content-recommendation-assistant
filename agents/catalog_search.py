"""Catalog Search Specialist Agent."""

from retrieval.catalog_provider import CatalogProvider
from schemas.responses import SpecialistOutput
from schemas.evidence import CatalogResult


class CatalogSearchAgent:
    """Specialist for catalog search and ranking."""

    def __init__(self, catalog_provider: CatalogProvider):
        """
        Initialize with catalog provider.

        Args:
            catalog_provider: Catalog provider instance
        """
        self.catalog = catalog_provider

    def search(self, query: str, top_k: int = 5) -> SpecialistOutput:
        """
        Search catalog and return ranked results.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            SpecialistOutput with ranked catalog results
        """
        results = self.catalog.search(query, top_k=top_k)

        return SpecialistOutput(
            specialist_name="CatalogSearch",
            results=results,
            metadata={
                "query": query,
                "top_k": top_k,
                "num_results": len(results),
            }
        )
