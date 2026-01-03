"""Context and metadata schemas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Classification of user question intent."""
    CATALOG_DISCOVERY = "catalog_discovery"
    RECOMMENDATION = "recommendation"
    SKILL_VALIDATION = "skill_validation"


class AudiencePersona(str, Enum):
    """Stakeholder persona for tailored responses."""
    CTO = "CTO"
    HR = "HR"
    L_AND_D = "L&D"


class CustomerContext(BaseModel):
    """Extracted context from user question."""
    roles: list[str] = Field(default_factory=list, description="Target job roles")
    scale: Optional[int] = Field(None, description="Number of learners")
    timeline_months: Optional[int] = Field(None, description="Timeline in months")
    hours_per_week: Optional[int] = Field(None, description="Available hours per week")
    hands_on_required: bool = Field(False, description="Hands-on practice required")
    skill_focus: list[str] = Field(default_factory=list, description="Specific skills needed")
    audience_persona: str = Field("non-technical", description="Technical vs non-technical")


class MergedContext(BaseModel):
    """Complete context passed to Composer."""
    user_question: str
    task_type: TaskType
    audience_persona: AudiencePersona
    customer_context: CustomerContext
    retrieved_evidence: dict = Field(default_factory=dict)
    constraints: dict = Field(
        default_factory=lambda: {"no_overclaim": True, "cite_sources": True}
    )
