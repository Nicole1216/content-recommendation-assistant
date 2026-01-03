"""Catalog provider interface with mocked implementation."""

from typing import Optional
from schemas.evidence import CatalogResult


class CatalogProvider:
    """Interface for catalog search (mocked for Phase 1)."""

    def __init__(self):
        """Initialize with mock data."""
        self._mock_catalog = self._create_mock_catalog()

    def _create_mock_catalog(self) -> list[CatalogResult]:
        """Create mock catalog data."""
        return [
            CatalogResult(
                program_key="cd0000",
                program_title="AI Programming with Python",
                program_type="Nanodegree",
                summary="Learn Python fundamentals and AI basics. Build neural networks from scratch.",
                duration_hours=120.0,
                difficulty_level="Beginner",
                fit_score=0.0,
            ),
            CatalogResult(
                program_key="cd0101",
                program_title="Generative AI for Business Leaders",
                program_type="Course",
                summary="Non-technical introduction to GenAI applications in business. No coding required.",
                duration_hours=8.0,
                difficulty_level="Beginner",
                fit_score=0.0,
            ),
            CatalogResult(
                program_key="cd0102",
                program_title="Data Analyst Nanodegree",
                program_type="Nanodegree",
                summary="Master SQL, Python, and data visualization. Build projects with real datasets.",
                duration_hours=180.0,
                difficulty_level="Intermediate",
                fit_score=0.0,
            ),
            CatalogResult(
                program_key="cd0103",
                program_title="GenAI Prompt Engineering",
                program_type="Course",
                summary="Learn prompt engineering techniques for ChatGPT, Claude, and enterprise LLMs.",
                duration_hours=12.0,
                difficulty_level="Beginner",
                fit_score=0.0,
            ),
            CatalogResult(
                program_key="cd0104",
                program_title="Machine Learning Engineer Nanodegree",
                program_type="Nanodegree",
                summary="Build production ML systems. Deploy models to cloud. Hands-on with AWS SageMaker.",
                duration_hours=240.0,
                difficulty_level="Advanced",
                fit_score=0.0,
            ),
            CatalogResult(
                program_key="cd0105",
                program_title="GenAI for Product Managers",
                program_type="Course",
                summary="Product strategy with GenAI. Use cases, ROI analysis, vendor selection. No coding.",
                duration_hours=10.0,
                difficulty_level="Beginner",
                fit_score=0.0,
            ),
        ]

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[dict] = None
    ) -> list[CatalogResult]:
        """
        Search catalog (mocked with keyword matching).

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional filters (not implemented in Phase 1)

        Returns:
            List of catalog results with fit scores
        """
        query_lower = query.lower()
        keywords = query_lower.split()

        # Simple keyword matching for mock
        results = []
        for item in self._mock_catalog:
            score = 0.0
            searchable_text = (
                f"{item.program_title} {item.summary} {item.program_type}"
            ).lower()

            for keyword in keywords:
                if keyword in searchable_text:
                    score += 1.0

            if score > 0:
                # Normalize score
                item_copy = item.model_copy()
                item_copy.fit_score = min(score / len(keywords), 1.0)
                results.append(item_copy)

        # Sort by fit score and return top_k
        results.sort(key=lambda x: x.fit_score, reverse=True)
        return results[:top_k]

    def get_by_key(self, program_key: str) -> Optional[CatalogResult]:
        """Get a specific program by key."""
        for item in self._mock_catalog:
            if item.program_key == program_key:
                return item.model_copy()
        return None
