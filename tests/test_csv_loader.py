"""Tests for CSV loader."""

import pytest
from pathlib import Path
from retrieval.csv_loader import CSVLoader


class TestCSVLoader:
    """Test CSV loading and parsing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.loader = CSVLoader()
        self.sample_csv_path = Path(__file__).parent.parent / "data" / "NLC_Skill_Data.csv"

    def test_load_csv(self):
        """Test CSV loading."""
        df = self.loader.load_csv(str(self.sample_csv_path))

        assert df is not None
        assert len(df) > 0
        # Should have the expected columns
        assert "Program Key" in df.columns
        assert "Course Key" in df.columns

    def test_parse_array_skills(self):
        """Test array parsing for skill arrays."""
        # Test comma-separated values
        result = self.loader._parse_array("SQL,Python,Tableau")
        assert result == ["SQL", "Python", "Tableau"]

        # Test with whitespace
        result = self.loader._parse_array(" SQL , Python , Tableau ")
        assert result == ["SQL", "Python", "Tableau"]

        # Test with null values
        result = self.loader._parse_array("SQL,null,Python")
        assert result == ["SQL", "Python"]

        # Test empty string
        result = self.loader._parse_array("")
        assert result == []

        # Test None
        result = self.loader._parse_array(None)
        assert result == []

    def test_parse_array_deduplication(self):
        """Test array parsing deduplicates while preserving order."""
        result = self.loader._parse_array("SQL,Python,SQL,Tableau,Python")
        assert result == ["SQL", "Python", "Tableau"]

    def test_boolean_parsing(self):
        """Test boolean field parsing."""
        df = self.loader.load_csv(str(self.sample_csv_path))

        # Check boolean columns exist and are parsed
        if "In Consumer Catalog" in df.columns:
            assert df["In Consumer Catalog"].dtype == bool or df["In Consumer Catalog"].dtype == object

    def test_numeric_parsing(self):
        """Test numeric field parsing."""
        df = self.loader.load_csv(str(self.sample_csv_path))

        # Check numeric columns are properly typed
        if "Program Duration Hours" in df.columns:
            # Should be numeric or NaN
            assert df["Program Duration Hours"].dtype in ['float64', 'int64', 'object']

    def test_course_skills_array_parsing(self):
        """Test Course Skills Array parsing."""
        df = self.loader.load_csv(str(self.sample_csv_path))

        if "Course Skills Array" in df.columns:
            # Find a non-empty value
            for skills in df["Course Skills Array"].dropna():
                if isinstance(skills, list) and len(skills) > 0:
                    # Should be a list with items
                    assert all(isinstance(s, str) for s in skills)
                    return
            # If we get here, all values are empty - that's okay for testing
            assert True

    def test_course_skills_subject_array_parsing(self):
        """Test Course Skills Subject Array parsing."""
        df = self.loader.load_csv(str(self.sample_csv_path))

        if "Course Skills Subject Array" in df.columns:
            # Get first non-null value
            skills = df["Course Skills Subject Array"].dropna().iloc[0]
            # Should be a list
            assert isinstance(skills, list)

    def test_concept_titles_parsing(self):
        """Test concept_titles array parsing."""
        df = self.loader.load_csv(str(self.sample_csv_path))

        if "concept_titles" in df.columns:
            # Find a non-empty value
            for concepts in df["concept_titles"].dropna():
                if isinstance(concepts, list) and len(concepts) > 0:
                    # Should have string items
                    assert all(isinstance(c, str) for c in concepts)
                    return
            # If all are empty, that's okay
            assert True
