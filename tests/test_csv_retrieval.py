"""Tests for CSV retrieval."""

import pytest
from retrieval.csv_index import CSVIndex


class TestCSVRetrieval:
    """Test CSV index retrieval."""

    def setup_method(self):
        """Set up test fixtures."""
        self.csv_index = CSVIndex()

    def test_get_details_single_program(self):
        """Test retrieving details for a single program."""
        results = self.csv_index.get_details(["cd0000"])

        assert len(results) == 1
        assert results[0].program_key == "cd0000"
        assert results[0].program_title == "AI Programming with Python"

    def test_get_details_multiple_programs(self):
        """Test retrieving details for multiple programs."""
        results = self.csv_index.get_details(["cd0000", "cd0102"])

        assert len(results) == 2
        keys = [r.program_key for r in results]
        assert "cd0000" in keys
        assert "cd0102" in keys

    def test_search_by_skill_python(self):
        """Test searching by Python skill."""
        results = self.csv_index.search_by_skill("Python")

        assert len(results) > 0
        # Check that at least one result has Python in skills
        has_python = any("Python" in r.course_skills for r in results)
        assert has_python

    def test_search_by_skill_genai(self):
        """Test searching by GenAI skill."""
        results = self.csv_index.search_by_skill("GenAI")

        assert len(results) > 0
        # Should find GenAI-related programs
        program_keys = [r.program_key for r in results]
        assert any(key in ["cd0101", "cd0103", "cd0105"] for key in program_keys)

    def test_search_by_tools(self):
        """Test searching by tools."""
        results = self.csv_index.search_by_tools("Jupyter")

        assert len(results) > 0
        # Check that results have Jupyter in tools
        has_jupyter = any("Jupyter" in r.third_party_tools for r in results)
        assert has_jupyter

    def test_prerequisite_skills_present(self):
        """Test that prerequisite skills are present in details."""
        results = self.csv_index.get_details(["cd0102"])

        assert len(results) == 1
        assert len(results[0].prerequisite_skills) > 0
        assert "Basic Excel" in results[0].prerequisite_skills

    def test_projects_present(self):
        """Test that project information is present."""
        results = self.csv_index.get_details(["cd0102"])

        assert len(results) == 1
        assert len(results[0].project_titles) > 0
        assert "Sales Dashboard" in results[0].project_titles
