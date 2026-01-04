"""Schemas for skill semantic resolution."""

from typing import Optional
from pydantic import BaseModel, Field


class SkillCandidate(BaseModel):
    """A candidate skill match with score and source."""
    skill: str = Field(description="Skill name")
    score: float = Field(ge=0.0, le=1.0, description="Match confidence score")
    source: str = Field(description="Source of match: alias, taxonomy, fuzzy, or embedding")
    canonical_skill: Optional[str] = Field(None, description="Canonical skill if from alias/taxonomy")
    intent_label: Optional[str] = Field(None, description="Intent label if from taxonomy")


class SkillSemanticResult(BaseModel):
    """Result of semantic skill resolution."""
    normalized_skills: list[str] = Field(
        default_factory=list,
        description="Normalized canonical skill names"
    )
    skill_intents: list[str] = Field(
        default_factory=list,
        description="Detected skill intents (e.g., python_analytics, sql_advanced)"
    )
    query_expansions: list[str] = Field(
        default_factory=list,
        description="Additional query terms to improve search"
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the resolution"
    )
    why: str = Field(
        "",
        description="Explanation of how skills were resolved"
    )
    candidates: list[SkillCandidate] = Field(
        default_factory=list,
        description="All candidate skills considered"
    )
    original_query: str = Field("", description="Original query text")
