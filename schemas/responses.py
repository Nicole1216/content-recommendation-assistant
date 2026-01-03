"""Agent response schemas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from .context import TaskType, CustomerContext, AudiencePersona


class RetrievalPlan(BaseModel):
    """Plan for data retrieval."""
    use_catalog: bool = True
    use_csv: bool = False
    catalog_query: Optional[str] = None
    csv_filters: dict = Field(default_factory=dict)
    top_k: int = 5


class RouterOutput(BaseModel):
    """Output from Router Agent."""
    task_type: TaskType
    customer_context: CustomerContext
    retrieval_plan: RetrievalPlan
    audience_persona: AudiencePersona


class SpecialistOutput(BaseModel):
    """Generic output from specialist agents."""
    specialist_name: str
    results: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ComposerOutput(BaseModel):
    """Output from Composer Agent."""
    response_text: str
    citations: list[str] = Field(default_factory=list)
    assumptions_and_gaps: list[str] = Field(default_factory=list)
    evaluation_questions_answered: dict[str, bool] = Field(default_factory=dict)


class CriticDecision(str, Enum):
    """Critic decision."""
    PASS = "PASS"
    REVISE = "REVISE"


class CriticOutput(BaseModel):
    """Output from Critic Agent."""
    decision: CriticDecision
    critique: list[str] = Field(default_factory=list)
    completeness_score: float = Field(0.0, ge=0.0, le=1.0)
    evidence_support_score: float = Field(0.0, ge=0.0, le=1.0)
    persona_fit_score: float = Field(0.0, ge=0.0, le=1.0)
