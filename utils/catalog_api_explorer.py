"""Utility to explore and retrieve data from the Udacity Catalog API."""

import requests
import json
from typing import Optional, List, Dict, Any


class CatalogAPIExplorer:
    """Explorer for the Udacity Unified Catalog API."""

    BASE_URL = "https://api.udacity.com/api/unified-catalog"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def search(
        self,
        query: str = "",
        page_size: int = 1000,
        sort_by: str = "avgRating",
        skill_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search the catalog.

        Args:
            query: Search query string (optional)
            page_size: Number of results to return (up to 1000)
            sort_by: Sort field (e.g., 'avgRating')
            skill_names: List of skill names to filter by

        Returns:
            API response as dictionary
        """
        payload = {
            "PageSize": page_size,
            "SortBy": sort_by,
        }

        if query:
            payload["query"] = query

        if skill_names:
            payload["SkillNames"] = skill_names

        response = self.session.post(
            f"{self.BASE_URL}/search",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def get_all_programs(self, public_only: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieve all programs from the catalog.

        Args:
            public_only: If True, filter to only publicly offered programs

        Returns:
            List of all programs
        """
        result = self.search(page_size=1000)
        hits = result.get("searchResult", {}).get("hits", [])

        if public_only:
            hits = [h for h in hits if h.get("is_offered_to_public")]

        return hits

    def get_all_skills(self) -> List[str]:
        """
        Extract all unique skills from the catalog.

        Returns:
            Sorted list of all skill names
        """
        programs = self.get_all_programs()
        skills = set()
        for prog in programs:
            for skill in prog.get("skill_names", []):
                skills.add(skill)
        return sorted(skills)

    def get_program_fields(self) -> List[str]:
        """
        Get all available fields in a program record.

        Returns:
            List of field names
        """
        result = self.search(page_size=1)
        hits = result.get("searchResult", {}).get("hits", [])

        if hits:
            return sorted(hits[0].keys())
        return []

    def search_by_skills(self, skills: List[str]) -> List[Dict[str, Any]]:
        """
        Search programs by skill names.

        Args:
            skills: List of skill names to search for

        Returns:
            List of matching programs
        """
        result = self.search(skill_names=skills)
        hits = result.get("searchResult", {}).get("hits", [])
        return [h for h in hits if h.get("is_offered_to_public")]

    def get_catalog_stats(self) -> Dict[str, Any]:
        """
        Get overall catalog statistics.

        Returns:
            Dictionary with catalog statistics
        """
        programs = self.get_all_programs()

        # Aggregate stats
        semantic_types = {}
        difficulties = {}
        with_skills = 0

        for prog in programs:
            st = prog.get("semantic_type", "Unknown")
            semantic_types[st] = semantic_types.get(st, 0) + 1

            diff = prog.get("difficulty") or "N/A"
            difficulties[diff] = difficulties.get(diff, 0) + 1

            if prog.get("skill_names"):
                with_skills += 1

        return {
            "total_programs": len(programs),
            "semantic_types": semantic_types,
            "difficulties": difficulties,
            "programs_with_skills": with_skills
        }

    def export_to_json(self, filename: str = "catalog_export.json"):
        """
        Export all available catalog data to JSON.

        Args:
            filename: Output filename
        """
        data = {
            "stats": self.get_catalog_stats(),
            "fields": self.get_program_fields(),
            "programs": self.get_all_programs()
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Exported {len(data['programs'])} programs to {filename}")
        return data


def main():
    """Run API exploration and print findings."""
    explorer = CatalogAPIExplorer()

    print("=" * 60)
    print("UDACITY CATALOG API EXPLORATION")
    print("=" * 60)

    # Get catalog stats
    print("\n1. CATALOG STATISTICS")
    print("-" * 40)
    stats = explorer.get_catalog_stats()
    print(f"Total Programs: {stats['total_programs']}")
    print(f"Programs with Skills: {stats['programs_with_skills']}")

    print("\nSemantic Types:")
    for t, c in sorted(stats['semantic_types'].items(), key=lambda x: -x[1]):
        print(f"  - {t}: {c}")

    print("\nDifficulties:")
    for d, c in sorted(stats['difficulties'].items(), key=lambda x: -x[1]):
        print(f"  - {d}: {c}")

    # Get available fields
    print("\n2. AVAILABLE FIELDS PER PROGRAM")
    print("-" * 40)
    fields = explorer.get_program_fields()
    for field in fields:
        print(f"  - {field}")

    # Get all skills
    print("\n3. ALL CATALOG SKILLS")
    print("-" * 40)
    skills = explorer.get_all_skills()
    print(f"Total unique skills: {len(skills)}")
    print(f"Sample skills: {skills[:20]}")

    # Get sample programs with skills
    print("\n4. SAMPLE PROGRAMS (Nanodegrees with skills)")
    print("-" * 40)
    programs = explorer.get_all_programs()
    nanodegrees = [p for p in programs if p.get('semantic_type') == 'Degree' and p.get('skill_names')]

    for prog in nanodegrees[:5]:
        print(f"\n  {prog.get('key')}: {prog.get('title')}")
        print(f"    Type: {prog.get('semantic_type')}")
        print(f"    Difficulty: {prog.get('difficulty')}")
        print(f"    Duration: {prog.get('raw_duration')} mins")
        print(f"    Rating: {prog.get('rating_average')} ({prog.get('rating_count')} reviews)")
        print(f"    Skills: {prog.get('skill_names')[:5]}...")

    print("\n" + "=" * 60)
    print("EXPLORATION COMPLETE")
    print("=" * 60)

    return explorer


if __name__ == "__main__":
    main()
