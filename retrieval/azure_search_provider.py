"""Azure AI Search based retrieval provider."""

import logging
import os
from typing import Optional, List, Dict, Any

from config.settings import Settings
from retrieval.azure.search_client import AzureSearchClient
from schemas.aggregated import ProgramEntity

logger = logging.getLogger(__name__)


class SearchResult:
    """Search result with program entity and score."""

    def __init__(self, program_entity: ProgramEntity, relevance_score: float):
        self.program_entity = program_entity
        self.relevance_score = relevance_score


class AzureSearchProvider:
    """Retrieval provider using Azure AI Search."""

    EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(
        self,
        settings: Optional[Settings] = None,
        azure_endpoint: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        index_name: str = "udacity-programs"
    ):
        """
        Initialize Azure Search provider.

        Args:
            settings: Application settings
            azure_endpoint: Azure Search endpoint (overrides settings)
            azure_api_key: Azure Search API key (overrides settings)
            openai_api_key: OpenAI API key for query embeddings
            index_name: Name of the search index
        """
        self.settings = settings or Settings()

        # Azure Search client
        endpoint = azure_endpoint or self.settings.azure_search_endpoint
        api_key = azure_api_key or self.settings.azure_search_api_key
        index = index_name or self.settings.azure_search_index

        self.search_client = AzureSearchClient(
            endpoint=endpoint,
            api_key=api_key,
            index_name=index
        )

        # OpenAI client for query embeddings
        self.openai_api_key = openai_api_key or self.settings.openai_api_key
        self.openai_client = None

        if self.openai_api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized for query embeddings")
            except ImportError:
                logger.warning("OpenAI package not installed")
        else:
            logger.warning("No OpenAI API key - query embeddings disabled")

        # Query embedding cache
        self._query_cache: Dict[str, List[float]] = {}
        self._cache_max_size = 100

    def is_available(self) -> bool:
        """Check if Azure Search is available."""
        return self.search_client.is_available() and self.openai_client is not None

    def _embed_query(self, query: str) -> Optional[List[float]]:
        """Generate embedding for query with caching."""
        if not self.openai_client:
            return None

        # Normalize for cache
        cache_key = query.strip().lower()

        # Check cache
        if cache_key in self._query_cache:
            logger.debug(f"Query embedding cache hit")
            return self._query_cache[cache_key]

        try:
            response = self.openai_client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=query
            )
            embedding = response.data[0].embedding

            # Add to cache
            if len(self._query_cache) >= self._cache_max_size:
                oldest_key = next(iter(self._query_cache))
                del self._query_cache[oldest_key]

            self._query_cache[cache_key] = embedding
            return embedding

        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            return None

    def _doc_to_program_entity(self, doc: Dict[str, Any]) -> ProgramEntity:
        """Convert Azure Search document to ProgramEntity."""
        # Parse skills from comma-separated string
        skills_str = doc.get("skills", "")
        skills = [s.strip() for s in skills_str.split(",") if s.strip()] if skills_str else []

        skill_subjects_str = doc.get("skill_subjects", "")
        skill_subjects = [s.strip() for s in skill_subjects_str.split(",") if s.strip()] if skill_subjects_str else []

        skill_domains_str = doc.get("skill_domains", "")
        skill_domains = [s.strip() for s in skill_domains_str.split(",") if s.strip()] if skill_domains_str else []

        return ProgramEntity(
            program_key=doc.get("program_key", ""),
            program_title=doc.get("program_title", ""),
            program_type=doc.get("program_type"),
            program_summary=doc.get("course_summary"),
            program_duration_hours=doc.get("duration_hours"),
            difficulty_level=doc.get("difficulty_level"),
            skills=skills,
            skill_subjects=skill_subjects,
            skill_domains=skill_domains,
            prerequisites=doc.get("prerequisites"),
            software_requirements=doc.get("software_requirements"),
            projects=[doc.get("projects")] if doc.get("projects") else [],
            courses=[]  # Not loading full course details
        )

    def search_programs(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for programs using vector similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional OData filter expression

        Returns:
            List of SearchResult objects
        """
        if not self.is_available():
            logger.warning("Azure Search not available")
            return []

        # Generate query embedding
        query_vector = self._embed_query(query)
        if not query_vector:
            logger.error("Failed to generate query embedding")
            return []

        # Perform hybrid search (vector + keyword)
        results = self.search_client.hybrid_search(
            query=query,
            query_vector=query_vector,
            top_k=top_k,
            filters=filters
        )

        # Convert to SearchResult objects
        search_results = []
        seen_programs = set()

        for doc in results:
            program_key = doc.get("program_key", "")

            # Deduplicate by program key
            if program_key in seen_programs:
                continue
            seen_programs.add(program_key)

            program = self._doc_to_program_entity(doc)
            score = doc.get("score", 0)

            # Normalize score to 0-1 range
            normalized_score = min(1.0, score / 10.0) if score > 0 else 0

            search_results.append(SearchResult(
                program_entity=program,
                relevance_score=normalized_score
            ))

        return search_results

    def get_program_details(self, program_keys: List[str]) -> List[ProgramEntity]:
        """
        Get detailed information for specific programs.

        Args:
            program_keys: List of program keys to retrieve

        Returns:
            List of ProgramEntity objects
        """
        if not self.search_client.is_available():
            return []

        programs = []

        for key in program_keys:
            # Search by program key filter
            results = self.search_client.vector_search(
                query_vector=[0.0] * 1536,  # Dummy vector for filter-only search
                top_k=10,
                filters=f"program_key eq '{key}'"
            )

            if results:
                # Take first result (should be exact match)
                program = self._doc_to_program_entity(results[0])
                programs.append(program)

        return programs

    def get_index_stats(self) -> Optional[Dict[str, Any]]:
        """Get index statistics."""
        return self.search_client.get_index_stats()
