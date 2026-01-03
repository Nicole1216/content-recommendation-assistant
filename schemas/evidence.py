"""Evidence and retrieval result schemas."""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class EvidenceSource(str, Enum):
    """Source of evidence."""
    CATALOG = "catalog"
    CSV = "csv"


class CatalogResult(BaseModel):
    """Result from catalog search."""
    program_key: str
    program_title: str
    program_type: str
    summary: str
    duration_hours: Optional[float] = None
    difficulty_level: Optional[str] = None
    fit_score: float = Field(0.0, ge=0.0, le=1.0, description="Relevance score")
    source: EvidenceSource = EvidenceSource.CATALOG


class CSVDetail(BaseModel):
    """Detailed information from CSV."""
    program_key: str
    program_title: str
    course_title: Optional[str] = None
    prerequisite_skills: list[str] = Field(default_factory=list)
    course_skills: list[str] = Field(default_factory=list)
    third_party_tools: list[str] = Field(default_factory=list)
    software_requirements: list[str] = Field(default_factory=list)
    hardware_requirements: list[str] = Field(default_factory=list)
    lesson_titles: list[str] = Field(default_factory=list)
    lesson_summaries: list[str] = Field(default_factory=list)
    project_titles: list[str] = Field(default_factory=list)
    concept_titles: list[str] = Field(default_factory=list)
    duration_hours: Optional[float] = None
    difficulty_level: Optional[str] = None
    source: EvidenceSource = EvidenceSource.CSV


class Comparison(BaseModel):
    """Comparison between programs."""
    program_a_key: str
    program_b_key: str
    differences: dict[str, Any] = Field(default_factory=dict)
    choose_a_if: list[str] = Field(default_factory=list)
    choose_b_if: list[str] = Field(default_factory=list)
    source: EvidenceSource = EvidenceSource.CSV


class Evidence(BaseModel):
    """Container for all evidence types."""
    catalog_results: list[CatalogResult] = Field(default_factory=list)
    csv_details: list[CSVDetail] = Field(default_factory=list)
    comparisons: list[Comparison] = Field(default_factory=list)
