"""Aggregated entity schemas for CSV data."""

from typing import Optional
from pydantic import BaseModel, Field


class CourseEntity(BaseModel):
    """Aggregated course entity from CSV."""
    program_key: str
    course_key: str
    course_title: str
    course_summary: Optional[str] = None

    # Critical skill arrays (FIRST-CLASS indices)
    course_skills_array: list[str] = Field(default_factory=list)
    course_skills_subject_array: list[str] = Field(default_factory=list)
    skill_domains: list[str] = Field(default_factory=list)  # High-level skill categories

    # Other course metadata
    course_prereq_skills: list[str] = Field(default_factory=list)
    third_party_tools: list[str] = Field(default_factory=list)
    software_requirements: list[str] = Field(default_factory=list)
    hardware_requirements: list[str] = Field(default_factory=list)
    course_duration_hours: Optional[float] = None

    # Lesson structure
    lesson_outline: list[str] = Field(default_factory=list, description="Ordered lesson titles")
    lesson_count: int = 0

    # Project information
    project_titles: list[str] = Field(default_factory=list)
    project_count: int = 0
    hands_on: bool = False

    # Concepts
    concept_titles: list[str] = Field(default_factory=list)


class ProgramEntity(BaseModel):
    """Aggregated program entity from CSV."""
    # Program identification
    program_key: str
    program_title: str
    program_type: Optional[str] = None

    # Program metadata
    program_summary: Optional[str] = None
    program_duration_hours: Optional[float] = None
    difficulty_level: Optional[str] = None
    primary_school: Optional[str] = None
    persona: Optional[str] = None
    program_url: Optional[str] = None
    program_category: Optional[str] = None
    syllabus_overview: Optional[str] = None

    # Catalog flags (MUST be exposed)
    in_consumer_catalog: bool = False
    in_ent_catalog: bool = False

    # Prerequisites (aggregated)
    program_prereq_skills: list[str] = Field(default_factory=list)

    # Skills union (from all courses)
    skills_union: list[str] = Field(
        default_factory=list,
        description="Union of all course_skills_array and course_skills_subject_array"
    )
    skill_domains: list[str] = Field(
        default_factory=list,
        description="High-level skill domains (e.g., AI, Data Science, Cloud)"
    )
    skills_by_course: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of course_key to skills taught in that course"
    )

    # Courses in program
    courses: list[str] = Field(default_factory=list, description="Distinct course keys")
    course_count: int = 0

    # Aggregated counts
    lesson_count: int = 0
    project_count: int = 0

    # Business metadata
    gtm_array: list[str] = Field(default_factory=list)
    partners: list[str] = Field(default_factory=list)
    clients: list[str] = Field(default_factory=list)
    version: Optional[str] = None
    version_released_at: Optional[str] = None
    total_active_enrollments: Optional[int] = None


class ProgramSearchResult(BaseModel):
    """Search result for a program with match evidence."""
    program_entity: ProgramEntity

    # Match evidence
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)
    matched_course_skills: list[str] = Field(default_factory=list)
    matched_course_skill_subjects: list[str] = Field(default_factory=list)
    matched_courses: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {course_key, course_title} that matched"
    )

    # Evidence tracking
    evidence_source: str = "csv"
    source_columns: list[str] = Field(default_factory=list)
