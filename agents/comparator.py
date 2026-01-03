"""Comparator Specialist Agent."""

from typing import Any
from schemas.responses import SpecialistOutput
from schemas.evidence import CSVDetail, Comparison


class ComparatorAgent:
    """Specialist for comparing programs."""

    def compare(self, program_a: CSVDetail, program_b: CSVDetail) -> Comparison:
        """
        Compare two programs across key dimensions.

        Args:
            program_a: First program
            program_b: Second program

        Returns:
            Comparison object with differences and recommendations
        """
        differences: dict[str, Any] = {}

        # Compare duration
        if program_a.duration_hours and program_b.duration_hours:
            differences["duration_hours"] = {
                program_a.program_key: program_a.duration_hours,
                program_b.program_key: program_b.duration_hours,
            }

        # Compare difficulty
        differences["difficulty_level"] = {
            program_a.program_key: program_a.difficulty_level,
            program_b.program_key: program_b.difficulty_level,
        }

        # Compare prerequisites
        differences["prerequisites"] = {
            program_a.program_key: program_a.prerequisite_skills,
            program_b.program_key: program_b.prerequisite_skills,
        }

        # Compare skills taught
        differences["skills_taught"] = {
            program_a.program_key: program_a.course_skills,
            program_b.program_key: program_b.course_skills,
        }

        # Compare tools
        differences["tools"] = {
            program_a.program_key: program_a.third_party_tools,
            program_b.program_key: program_b.third_party_tools,
        }

        # Compare hands-on elements
        differences["projects"] = {
            program_a.program_key: program_a.project_titles,
            program_b.program_key: program_b.project_titles,
        }

        # Generate recommendations
        choose_a_if = []
        choose_b_if = []

        # Duration-based
        if program_a.duration_hours and program_b.duration_hours:
            if program_a.duration_hours < program_b.duration_hours:
                choose_a_if.append("Shorter timeline needed")
                choose_b_if.append("More comprehensive depth needed")
            else:
                choose_b_if.append("Shorter timeline needed")
                choose_a_if.append("More comprehensive depth needed")

        # Difficulty-based
        if program_a.difficulty_level == "Beginner" and program_b.difficulty_level != "Beginner":
            choose_a_if.append("Learners are new to the field")
            choose_b_if.append("Learners have prior experience")
        elif program_b.difficulty_level == "Beginner" and program_a.difficulty_level != "Beginner":
            choose_b_if.append("Learners are new to the field")
            choose_a_if.append("Learners have prior experience")

        # Prerequisites-based
        if len(program_a.prerequisite_skills) < len(program_b.prerequisite_skills):
            choose_a_if.append("Minimal prerequisites available")
        elif len(program_b.prerequisite_skills) < len(program_a.prerequisite_skills):
            choose_b_if.append("Minimal prerequisites available")

        # Hands-on-based
        if len(program_a.project_titles) > len(program_b.project_titles):
            choose_a_if.append("Hands-on practice is critical")
        elif len(program_b.project_titles) > len(program_a.project_titles):
            choose_b_if.append("Hands-on practice is critical")

        return Comparison(
            program_a_key=program_a.program_key,
            program_b_key=program_b.program_key,
            differences=differences,
            choose_a_if=choose_a_if,
            choose_b_if=choose_b_if,
        )

    def compare_multiple(self, programs: list[CSVDetail]) -> SpecialistOutput:
        """
        Compare multiple programs.

        Args:
            programs: List of programs to compare

        Returns:
            SpecialistOutput with comparisons
        """
        comparisons = []

        # Compare first program with all others
        if len(programs) >= 2:
            for i in range(1, len(programs)):
                comparison = self.compare(programs[0], programs[i])
                comparisons.append(comparison)

        return SpecialistOutput(
            specialist_name="Comparator",
            results=comparisons,
            metadata={
                "num_programs": len(programs),
                "num_comparisons": len(comparisons),
            }
        )
