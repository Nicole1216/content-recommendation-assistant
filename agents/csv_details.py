"""CSV Details Specialist Agent."""

from retrieval.csv_index import CSVIndex
from schemas.responses import SpecialistOutput
from schemas.evidence import CSVDetail


class CSVDetailsAgent:
    """Specialist for CSV detail retrieval."""

    def __init__(self, csv_index: CSVIndex):
        """
        Initialize with CSV index.

        Args:
            csv_index: CSV index instance
        """
        self.csv_index = csv_index

    def get_details(self, program_keys: list[str]) -> SpecialistOutput:
        """
        Get detailed information for programs.

        Args:
            program_keys: List of program keys

        Returns:
            SpecialistOutput with CSV details
        """
        details = self.csv_index.get_details(program_keys)

        return SpecialistOutput(
            specialist_name="CSVDetails",
            results=details,
            metadata={
                "program_keys": program_keys,
                "num_results": len(details),
            }
        )

    def search_by_skill(self, skill: str, top_k: int = 5) -> SpecialistOutput:
        """
        Search by skill.

        Args:
            skill: Skill to search for
            top_k: Number of results

        Returns:
            SpecialistOutput with matching programs
        """
        results = self.csv_index.search_by_skill(skill, top_k=top_k)

        return SpecialistOutput(
            specialist_name="CSVDetails",
            results=results,
            metadata={
                "skill": skill,
                "top_k": top_k,
                "num_results": len(results),
            }
        )
