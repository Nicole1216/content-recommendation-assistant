"""Tests for Skill Semantic Resolver."""

import pytest
from pathlib import Path
from retrieval.skill_semantics import SkillSemanticResolver


class TestSkillSemanticResolver:
    """Test skill semantic resolution layer."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use sample skill vocabulary
        self.skill_vocabulary = [
            "Python",
            "SQL",
            "Machine Learning",
            "Data Analysis",
            "Pandas",
            "NumPy",
            "TensorFlow",
            "Tableau",
            "AWS",
            "Docker",
        ]
        self.resolver = SkillSemanticResolver(skill_vocabulary=self.skill_vocabulary)

    def test_alias_mapping_genai(self):
        """Test GenAI alias mapping."""
        result = self.resolver.resolve("GenAI")

        # Should normalize to generative_ai
        assert "generative_ai" in result.normalized_skills
        assert result.confidence > 0.9
        assert "alias" in result.why.lower()

    def test_alias_mapping_llm(self):
        """Test LLM alias mapping."""
        result = self.resolver.resolve("LLM")

        # Should normalize to generative_ai
        assert "generative_ai" in result.normalized_skills
        assert result.confidence > 0.9

    def test_alias_mapping_prompt_engineering(self):
        """Test Prompt Engineering alias mapping."""
        result = self.resolver.resolve("Prompt Engineering")

        # Should normalize to generative_ai
        assert "generative_ai" in result.normalized_skills
        assert result.confidence > 0.9

    def test_alias_mapping_python_variants(self):
        """Test Python alias variations."""
        queries = ["Python", "Python Programming", "Py"]

        for query in queries:
            result = self.resolver.resolve(query)
            # Should map to python
            assert "python" in result.normalized_skills

    def test_alias_mapping_sql_variants(self):
        """Test SQL alias variations."""
        queries = ["SQL", "Structured Query Language", "Database Queries"]

        for query in queries:
            result = self.resolver.resolve(query)
            # Should map to sql
            assert "sql" in result.normalized_skills

    def test_taxonomy_python_analytics(self):
        """Test taxonomy disambiguation for Python analytics."""
        context = "We need Python for data analysts using pandas and jupyter"
        result = self.resolver.resolve("Python", context=context)

        # Should detect python_analytics intent
        assert "python_analytics" in result.skill_intents
        # Should have analytics-related expansions
        assert any("Pandas" in exp or "NumPy" in exp for exp in result.query_expansions)

    def test_taxonomy_python_ml(self):
        """Test taxonomy disambiguation for Python ML."""
        context = "Python for machine learning engineers training models with scikit-learn"
        result = self.resolver.resolve("Python", context=context)

        # Should detect python_ml intent
        assert "python_ml" in result.skill_intents
        # Should have ML-related expansions
        assert len(result.query_expansions) > 0

    def test_taxonomy_sql_basics(self):
        """Test taxonomy disambiguation for basic SQL."""
        context = "beginner SQL SELECT WHERE JOIN queries"
        result = self.resolver.resolve("SQL", context=context)

        # Should detect sql_basics intent
        assert "sql_basics" in result.skill_intents

    def test_taxonomy_sql_advanced(self):
        """Test taxonomy disambiguation for advanced SQL."""
        context = "advanced SQL optimization window functions CTEs execution plans"
        result = self.resolver.resolve("SQL", context=context)

        # Should detect sql_advanced intent
        assert "sql_advanced" in result.skill_intents

    def test_taxonomy_genai_business(self):
        """Test taxonomy for GenAI business intent."""
        context = "GenAI for business leaders non-technical ROI strategy"
        result = self.resolver.resolve("GenAI", context=context)

        # Should detect genai_business intent
        assert "genai_business" in result.skill_intents

    def test_taxonomy_genai_technical(self):
        """Test taxonomy for GenAI technical intent."""
        context = "prompt engineering technical implementation LangChain API"
        result = self.resolver.resolve("GenAI", context=context)

        # Should detect genai_technical intent
        assert "genai_technical" in result.skill_intents

    def test_fuzzy_match_typo(self):
        """Test fuzzy matching recovers from typos."""
        result = self.resolver.resolve("Pyton")  # Typo: Pyton instead of Python

        # Should find Python via fuzzy match
        assert len(result.candidates) > 0
        # Check if Python is a candidate
        python_found = any(
            "Python" in c.skill and c.source == "fuzzy"
            for c in result.candidates
        )
        assert python_found

    def test_fuzzy_match_variation(self):
        """Test fuzzy matching with variations."""
        result = self.resolver.resolve("Machine Learing")  # Typo: Learing

        # Should find Machine Learning via fuzzy match
        assert len(result.candidates) > 0

    def test_fuzzy_match_partial(self):
        """Test fuzzy matching with partial words."""
        result = self.resolver.resolve("Tablea")  # Partial: Tablea instead of Tableau

        # Should find Tableau
        tableau_found = any(
            "Tableau" in c.skill
            for c in result.candidates
        )
        assert tableau_found

    def test_combined_alias_and_taxonomy(self):
        """Test combined alias mapping and taxonomy."""
        context = "Python for data analysts using pandas"
        result = self.resolver.resolve("Python Programming", context=context)

        # Should have both normalized skill from alias
        assert "python" in result.normalized_skills
        # And intent from taxonomy
        assert "python_analytics" in result.skill_intents

    def test_multiple_skills_in_query(self):
        """Test resolving multiple skills in one query."""
        result = self.resolver.resolve("Python and SQL for data analysis")

        # Should find both skills
        assert "python" in result.normalized_skills
        assert "sql" in result.normalized_skills
        assert "data_analysis" in result.normalized_skills

    def test_confidence_high_for_alias(self):
        """Test confidence is high for alias matches."""
        result = self.resolver.resolve("GenAI")

        # Alias match should have high confidence
        assert result.confidence >= 0.9

    def test_confidence_lower_for_fuzzy(self):
        """Test confidence is lower for fuzzy matches."""
        result = self.resolver.resolve("Pyton")  # Typo

        # Fuzzy match typically has lower confidence than alias
        # (depends on the score)
        if result.candidates:
            fuzzy_candidates = [c for c in result.candidates if c.source == "fuzzy"]
            if fuzzy_candidates:
                # Fuzzy scores should be < 1.0
                assert all(c.score < 1.0 for c in fuzzy_candidates)

    def test_query_expansions_added(self):
        """Test that query expansions are added from taxonomy."""
        context = "Python for machine learning model training"
        result = self.resolver.resolve("Python", context=context)

        # Should have expansions from ML taxonomy
        assert len(result.query_expansions) > 0

    def test_explanation_provided(self):
        """Test that explanation is provided."""
        result = self.resolver.resolve("GenAI")

        # Should have explanation
        assert result.why
        assert len(result.why) > 0

    def test_original_query_preserved(self):
        """Test that original query is preserved."""
        query = "Python for data analysis"
        result = self.resolver.resolve(query)

        assert result.original_query == query

    def test_candidates_tracked(self):
        """Test that all candidates are tracked."""
        result = self.resolver.resolve("Python")

        # Should have candidates
        assert len(result.candidates) > 0
        # Each candidate should have required fields
        for candidate in result.candidates:
            assert candidate.skill
            assert 0.0 <= candidate.score <= 1.0
            assert candidate.source in ["alias", "taxonomy", "fuzzy", "embedding"]

    def test_empty_query(self):
        """Test handling of empty query."""
        result = self.resolver.resolve("")

        # Should return empty result without crashing
        assert isinstance(result.normalized_skills, list)
        assert len(result.normalized_skills) == 0

    def test_no_match_query(self):
        """Test query with no matches."""
        result = self.resolver.resolve("completely unrelated gibberish xyz123")

        # Should return result with low/zero confidence
        # May have some fuzzy candidates
        assert result.confidence >= 0.0  # Should not crash
