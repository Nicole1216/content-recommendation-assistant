"""Tools for ReAct loop."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """Result from tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None


class Tool(ABC):
    """Abstract base class for tools."""
    name: str
    description: str
    parameters: Dict[str, Any]

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments."""
        pass

    def get_definition(self) -> Dict:
        """Get OpenAI-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class SearchProgramsTool(Tool):
    """Tool for searching programs by query."""

    name = "search_programs"
    description = """Search for Udacity programs matching a query.
Use this to find relevant courses and programs based on skills, topics, or roles.
Returns a list of matching programs with relevance scores."""

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (skills, topics, job roles, technologies)"
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default: 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }

    def __init__(self, csv_provider):
        """
        Initialize search tool.

        Args:
            csv_provider: RealCSVProvider instance
        """
        self.csv_provider = csv_provider

    def execute(self, query: str, top_k: int = 5) -> ToolResult:
        """Search for programs."""
        try:
            results = self.csv_provider.search_programs(query, top_k)

            # Format results for LLM consumption
            formatted = []
            for r in results:
                prog = r.program_entity
                formatted.append({
                    "program_key": prog.program_key,
                    "program_title": prog.program_title,
                    "program_type": prog.program_type,
                    "duration_hours": prog.program_duration_hours,
                    "difficulty_level": prog.difficulty_level,
                    "relevance_score": round(r.relevance_score, 2),
                    "matched_skills": r.matched_course_skills[:10],  # Limit for context
                    "skill_domains": prog.skill_domains[:5] if prog.skill_domains else [],
                    "summary": (prog.program_summary or "")[:300]  # Truncate
                })

            return ToolResult(
                tool_name=self.name,
                success=True,
                result=formatted
            )
        except Exception as e:
            logger.error(f"Search tool error: {e}")
            return ToolResult(
                tool_name=self.name,
                success=False,
                result=None,
                error=str(e)
            )


class GetProgramDetailsTool(Tool):
    """Tool for getting detailed program information."""

    name = "get_program_details"
    description = """Get detailed information about specific programs.
Use this after searching to get full details including:
- Complete skill list
- Prerequisites
- Tools and technologies
- Lesson structure
- Project information"""

    parameters = {
        "type": "object",
        "properties": {
            "program_keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of program keys to get details for"
            }
        },
        "required": ["program_keys"]
    }

    def __init__(self, csv_provider):
        """
        Initialize details tool.

        Args:
            csv_provider: RealCSVProvider instance
        """
        self.csv_provider = csv_provider

    def execute(self, program_keys: List[str]) -> ToolResult:
        """Get program details."""
        try:
            details = self.csv_provider.get_details(program_keys)

            # Format for LLM
            formatted = []
            for d in details:
                formatted.append({
                    "program_key": d.program_key,
                    "program_title": d.program_title,
                    "course_title": d.course_title,
                    "duration_hours": d.duration_hours,
                    "difficulty_level": d.difficulty_level,
                    "prerequisite_skills": d.prerequisite_skills,
                    "course_skills": d.course_skills[:20],  # Limit
                    "third_party_tools": d.third_party_tools,
                    "software_requirements": d.software_requirements,
                    "lesson_count": len(d.lesson_titles),
                    "lesson_titles": d.lesson_titles[:10],  # First 10 lessons
                    "project_titles": d.project_titles,
                    "project_count": len(d.project_titles)
                })

            return ToolResult(
                tool_name=self.name,
                success=True,
                result=formatted
            )
        except Exception as e:
            logger.error(f"Details tool error: {e}")
            return ToolResult(
                tool_name=self.name,
                success=False,
                result=None,
                error=str(e)
            )


class CompareProgramsTool(Tool):
    """Tool for comparing multiple programs."""

    name = "compare_programs"
    description = """Compare two or more programs to understand their differences.
Use this when the user needs to choose between options.
Returns comparison of duration, difficulty, skills, and recommendations for when to choose each."""

    parameters = {
        "type": "object",
        "properties": {
            "program_keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of program keys to compare (2-4 programs)",
                "minItems": 2,
                "maxItems": 4
            }
        },
        "required": ["program_keys"]
    }

    def __init__(self, csv_provider):
        """
        Initialize comparison tool.

        Args:
            csv_provider: RealCSVProvider instance
        """
        self.csv_provider = csv_provider

    def execute(self, program_keys: List[str]) -> ToolResult:
        """Compare programs."""
        try:
            # Get details for all programs
            details = self.csv_provider.get_details(program_keys)

            if len(details) < 2:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    result=None,
                    error="Need at least 2 programs to compare"
                )

            # Build comparison
            comparisons = []
            for i, prog_a in enumerate(details):
                for prog_b in details[i+1:]:
                    comparison = self._compare_two(prog_a, prog_b)
                    comparisons.append(comparison)

            return ToolResult(
                tool_name=self.name,
                success=True,
                result=comparisons
            )
        except Exception as e:
            logger.error(f"Compare tool error: {e}")
            return ToolResult(
                tool_name=self.name,
                success=False,
                result=None,
                error=str(e)
            )

    def _compare_two(self, prog_a, prog_b) -> Dict:
        """Compare two programs."""
        # Skills comparison
        skills_a = set(prog_a.course_skills)
        skills_b = set(prog_b.course_skills)
        common_skills = skills_a & skills_b
        unique_a = skills_a - skills_b
        unique_b = skills_b - skills_a

        # Build comparison
        comparison = {
            "programs": [prog_a.program_key, prog_b.program_key],
            "titles": [prog_a.program_title, prog_b.program_title],
            "duration_comparison": {
                prog_a.program_key: prog_a.duration_hours,
                prog_b.program_key: prog_b.duration_hours
            },
            "difficulty_comparison": {
                prog_a.program_key: prog_a.difficulty_level,
                prog_b.program_key: prog_b.difficulty_level
            },
            "common_skills": list(common_skills)[:10],
            "unique_skills": {
                prog_a.program_key: list(unique_a)[:10],
                prog_b.program_key: list(unique_b)[:10]
            },
            "project_count": {
                prog_a.program_key: len(prog_a.project_titles),
                prog_b.program_key: len(prog_b.project_titles)
            },
            "choose_a_if": [],
            "choose_b_if": []
        }

        # Generate recommendations
        if prog_a.duration_hours and prog_b.duration_hours:
            if prog_a.duration_hours < prog_b.duration_hours:
                comparison["choose_a_if"].append("Shorter timeline needed")
                comparison["choose_b_if"].append("More comprehensive coverage needed")
            else:
                comparison["choose_b_if"].append("Shorter timeline needed")
                comparison["choose_a_if"].append("More comprehensive coverage needed")

        if len(prog_a.project_titles) > len(prog_b.project_titles):
            comparison["choose_a_if"].append("More hands-on projects preferred")
        elif len(prog_b.project_titles) > len(prog_a.project_titles):
            comparison["choose_b_if"].append("More hands-on projects preferred")

        return comparison
