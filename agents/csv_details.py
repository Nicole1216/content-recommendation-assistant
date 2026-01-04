"""CSV Details Specialist Agent."""

from retrieval.real_csv_provider import RealCSVProvider
from schemas.responses import SpecialistOutput


class CSVDetailsAgent:
    """Specialist for CSV detail retrieval."""

    def __init__(self, csv_provider: RealCSVProvider):
        """
        Initialize with CSV provider.

        Args:
            csv_provider: RealCSVProvider instance
        """
        self.csv_provider = csv_provider

    def get_details(self, program_keys: list[str]) -> SpecialistOutput:
        """
        Get detailed information for programs.

        Args:
            program_keys: List of program keys

        Returns:
            SpecialistOutput with CSV details
        """
        details = self.csv_provider.get_details(program_keys)

        return SpecialistOutput(
            specialist_name="CSVDetails",
            results=details,
            metadata={
                "program_keys": program_keys,
                "num_results": len(details),
            }
        )
