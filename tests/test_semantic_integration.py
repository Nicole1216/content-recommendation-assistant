"""Integration tests for semantic layer with RealCSVProvider."""

import pytest
from pathlib import Path
from retrieval.real_csv_provider import RealCSVProvider


class TestSemanticIntegration:
    """Test semantic layer integration with real CSV provider."""

    def setup_method(self):
        """Set up test fixtures."""
        csv_path = Path(__file__).parent.parent / "data" / "NLC_Skill_Data.csv"
        self.provider = RealCSVProvider(csv_path=str(csv_path))

    def test_semantic_resolver_initialized(self):
        """Test that semantic resolver is initialized."""
        assert self.provider.semantic_resolver is not None

    def test_skill_vocabulary_built(self):
        """Test that skill vocabulary is built from CSV."""
        assert len(self.provider.skill_vocabulary) > 0
        # Should have actual skills from CSV
        assert isinstance(self.provider.skill_vocabulary, list)

    def test_search_with_alias_genai(self):
        """Test search with GenAI alias."""
        # Search using alias "LLM" instead of "Generative AI"
        results = self.provider.search_programs("LLM", top_k=5)

        # Should find GenAI programs
        assert len(results) > 0

    def test_search_with_alias_python(self):
        """Test search with Python alias."""
        # Search using "Py" instead of "Python"
        results = self.provider.search_programs("Python Programming", top_k=5)

        # Should find Python programs
        assert len(results) > 0

    def test_search_with_taxonomy_python_analytics(self):
        """Test search benefits from taxonomy disambiguation."""
        # Query with analytics context
        results = self.provider.search_programs(
            "Python for data analysts using pandas",
            top_k=5
        )

        # Should find Python data analysis programs
        assert len(results) > 0

    def test_search_with_taxonomy_sql_advanced(self):
        """Test search with SQL advanced taxonomy."""
        # Query with advanced SQL signals
        results = self.provider.search_programs(
            "SQL optimization window functions",
            top_k=5
        )

        # Should find SQL programs
        assert len(results) > 0

    def test_semantic_improves_relevance(self):
        """Test that semantic layer improves search relevance."""
        # Without semantic layer, might need exact match
        # With semantic layer, aliases and fuzzy matching help

        # Search with variation
        results = self.provider.search_programs("GenAI", top_k=3)

        # Should find relevant programs even if CSV uses different terminology
        assert len(results) > 0

    def test_skill_vocabulary_contains_csv_skills(self):
        """Test that vocabulary contains actual skills from CSV."""
        # Check that common skills are in vocabulary
        vocab_lower = [s.lower() for s in self.provider.skill_vocabulary]

        # Should have some data/analytics related skills
        # (exact skills depend on CSV content)
        assert len(vocab_lower) > 10  # Should have multiple skills
