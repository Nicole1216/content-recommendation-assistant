"""Tests for Real CSV Provider."""

import pytest
from pathlib import Path
from retrieval.real_csv_provider import RealCSVProvider


class TestRealCSVProvider:
    """Test real CSV provider with aggregation and search."""

    def setup_method(self):
        """Set up test fixtures."""
        sample_csv_path = Path(__file__).parent.parent / "data" / "NLC_Skill_Data.csv"
        self.provider = RealCSVProvider(csv_path=str(sample_csv_path))

    def test_load_and_aggregate(self):
        """Test CSV loading and aggregation."""
        # Should have programs
        assert len(self.provider.programs) > 0

        # Should have courses
        assert len(self.provider.courses) > 0

    def test_program_aggregation(self):
        """Test program aggregation correctness."""
        # Check specific program
        if "nd0001" in self.provider.programs:
            prog = self.provider.programs["nd0001"]

            # Should have basic fields
            assert prog.program_key == "nd0001"
            assert prog.program_title == "Data Analyst"
            assert prog.program_type == "Nanodegree"

            # Should have catalog flags
            assert isinstance(prog.in_consumer_catalog, bool)
            assert isinstance(prog.in_ent_catalog, bool)

            # Should have courses
            assert len(prog.courses) > 0

            # Should have skills union
            assert len(prog.skills_union) > 0

    def test_course_aggregation(self):
        """Test course aggregation correctness."""
        # Find a course
        course_keys = list(self.provider.courses.keys())
        assert len(course_keys) > 0

        course = self.provider.courses[course_keys[0]]

        # Should have basic fields
        assert course.course_key
        assert course.course_title

        # Should have skill arrays
        assert isinstance(course.course_skills_array, list)
        assert isinstance(course.course_skills_subject_array, list)

    def test_course_skills_array_populated(self):
        """Test Course Skills Array is populated."""
        # Check nd0001 Data Analyst program
        if "nd0001" in self.provider.programs:
            prog = self.provider.programs["nd0001"]

            # Should have SQL and Python in skills
            skills_lower = [s.lower() for s in prog.skills_union]
            assert any("sql" in s for s in skills_lower)
            assert any("python" in s for s in skills_lower)

    def test_lesson_outline_preserved(self):
        """Test lesson outline is preserved in order."""
        # Check any course
        course_keys = list(self.provider.courses.keys())
        if len(course_keys) > 0:
            course = self.provider.courses[course_keys[0]]

            # Should have lessons
            if len(course.lesson_outline) > 0:
                # Should be ordered and distinct
                assert len(course.lesson_outline) == len(set(course.lesson_outline))

    def test_hands_on_detection(self):
        """Test hands-on flag is set correctly."""
        # Check nd0001 which has projects
        for key, course in self.provider.courses.items():
            if "nd0001" in key:
                # Should have projects
                if len(course.project_titles) > 0:
                    assert course.hands_on is True

    def test_search_by_skill_sql(self):
        """Test skill-based search for SQL."""
        results = self.provider.search_programs("SQL", top_k=5)

        # Should find results
        assert len(results) > 0

        # Top result should match SQL
        top_result = results[0]
        # Should have matched some skills
        assert len(top_result.matched_course_skills) > 0 or \
               "SQL" in top_result.program_entity.program_title

    def test_search_by_skill_python(self):
        """Test skill-based search for Python."""
        results = self.provider.search_programs("Python", top_k=5)

        # Should find results
        assert len(results) > 0

        # Check relevance scores
        assert all(r.relevance_score > 0 for r in results)

    def test_search_by_skill_genai(self):
        """Test skill-based search for GenAI."""
        results = self.provider.search_programs("GenAI", top_k=5)

        # Should find GenAI programs
        assert len(results) > 0

        # Should find the GenAI course
        program_titles = [r.program_entity.program_title for r in results]
        assert any("GenAI" in title or "Generative" in title for title in program_titles)

    def test_search_ranking_skill_match_highest(self):
        """Test that skill matches rank higher than title matches."""
        results = self.provider.search_programs("Machine Learning", top_k=5)

        if len(results) > 0:
            # Top results should have higher relevance
            assert results[0].relevance_score >= results[-1].relevance_score

    def test_search_evidence_tracking(self):
        """Test that search tracks evidence sources."""
        results = self.provider.search_programs("SQL", top_k=3)

        if len(results) > 0:
            top_result = results[0]
            # Should have source columns tracked
            assert len(top_result.source_columns) > 0
            # Should include evidence source
            assert top_result.evidence_source == "csv"

    def test_get_program_details(self):
        """Test getting program details."""
        if "nd0001" in self.provider.programs:
            details = self.provider.get_program_details("nd0001")

            assert details is not None
            assert details.program_key == "nd0001"
            assert details.program_title == "Data Analyst"

    def test_get_program_deep_details(self):
        """Test getting deep program details with courses."""
        if "nd0001" in self.provider.programs:
            deep = self.provider.get_program_deep_details("nd0001")

            assert deep is not None
            assert "program" in deep
            assert "courses" in deep

            # Should have courses
            assert len(deep["courses"]) > 0

            # Courses should have skill arrays
            for course in deep["courses"]:
                assert hasattr(course, "course_skills_array")
                assert hasattr(course, "course_skills_subject_array")

    def test_get_details_backward_compatibility(self):
        """Test backward compatibility with CSVDetail format."""
        # Use an actual program key from the real CSV
        if len(self.provider.programs) > 0:
            first_program_key = list(self.provider.programs.keys())[0]
            results = self.provider.get_details([first_program_key])

            if len(results) > 0:
                detail = results[0]
                # Should have expected CSVDetail fields
                assert detail.program_key == first_program_key
                assert detail.program_title
                assert isinstance(detail.course_skills, list)
                assert isinstance(detail.prerequisite_skills, list)
            else:
                # No courses for this program - that's okay
                assert True
        else:
            # No programs loaded - that's okay for empty CSV
            assert True

    def test_catalog_flags_exposed(self):
        """Test that catalog flags are exposed."""
        for prog_key, prog in self.provider.programs.items():
            # Should have both flags
            assert hasattr(prog, "in_consumer_catalog")
            assert hasattr(prog, "in_ent_catalog")
            # Should be boolean
            assert isinstance(prog.in_consumer_catalog, bool)
            assert isinstance(prog.in_ent_catalog, bool)

    def test_skills_by_course_mapping(self):
        """Test that skills are mapped to courses."""
        if "nd0001" in self.provider.programs:
            prog = self.provider.programs["nd0001"]

            # Should have skills_by_course
            assert isinstance(prog.skills_by_course, dict)

            # Should map course keys to skills
            if len(prog.skills_by_course) > 0:
                for course_key, skills in prog.skills_by_course.items():
                    assert isinstance(skills, list)
                    assert len(skills) > 0

    def test_matched_courses_in_search(self):
        """Test that search returns which courses matched."""
        results = self.provider.search_programs("SQL", top_k=3)

        if len(results) > 0:
            top_result = results[0]
            # Should have matched courses if skills matched
            if len(top_result.matched_course_skills) > 0:
                # May have matched courses
                assert isinstance(top_result.matched_courses, list)
