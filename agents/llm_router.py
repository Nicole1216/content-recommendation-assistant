"""LLM-based router agent for intelligent query classification."""

import json
import logging
from typing import Optional

from llm.base_client import BaseLLMClient, Message
from schemas.context import TaskType, CustomerContext, AudiencePersona
from schemas.responses import RouterOutput, RetrievalPlan

logger = logging.getLogger(__name__)


class LLMRouterAgent:
    """
    LLM-based router for intelligent query understanding.

    Replaces regex-based routing with LLM reasoning for:
    - Complex query interpretation
    - Career transition understanding
    - Customer context extraction
    """

    SYSTEM_PROMPT = """You are a query analyzer for a sales enablement system.
Your job is to understand the user's question and classify it correctly.

## Task Types
1. "catalog_discovery" - User wants to explore what programs are available
   Examples: "What courses do we offer?", "Show me AI programs", "List data science options"

2. "recommendation" - User needs specific recommendations for a customer
   Examples: "What should I recommend for...", "Customer wants to upskill their team", "Best program for..."

3. "skill_validation" - User wants to verify if we cover specific skills
   Examples: "Do we cover Kubernetes?", "How deep is our Python content?", "Can we teach TensorFlow?"

## Career Transition Queries
For queries like "transition from X to Y" or "upskill X to become Y":
- Focus on the TARGET role (Y) for skills matching
- Note the SOURCE role (X) as existing knowledge
- These are typically "recommendation" task types

## Customer Context Extraction
Extract these details if mentioned:
- roles: Job titles mentioned (e.g., "data analysts", "software engineers")
- scale: Number of learners (e.g., "50 employees", "team of 20")
- timeline_months: Timeline mentioned (e.g., "3 months", "by Q2")
- hours_per_week: Study commitment (e.g., "10 hours/week")
- skill_focus: Specific skills requested (e.g., "Python", "machine learning")
- hands_on_required: Whether projects/labs are emphasized

## Response Format
Respond with valid JSON only:
{
  "task_type": "catalog_discovery" | "recommendation" | "skill_validation",
  "customer_context": {
    "roles": ["role1", "role2"],
    "scale": 50,
    "timeline_months": 3,
    "hours_per_week": 10,
    "skill_focus": ["skill1", "skill2"],
    "hands_on_required": true
  },
  "retrieval_plan": {
    "use_catalog": true,
    "use_csv": true,
    "top_k": 5
  },
  "reasoning": "Brief explanation of classification"
}"""

    def __init__(self, llm_client: BaseLLMClient):
        """
        Initialize LLM router.

        Args:
            llm_client: LLM client for reasoning
        """
        self.llm_client = llm_client

    def route(
        self,
        question: str,
        persona: AudiencePersona,
        company_name: Optional[str] = None
    ) -> RouterOutput:
        """
        Route a question using LLM reasoning.

        Args:
            question: User's question
            persona: Audience persona
            company_name: Optional company name

        Returns:
            RouterOutput with classification and context
        """
        # Build context for LLM
        context_parts = [f"Persona: {persona.value}"]
        if company_name:
            context_parts.append(f"Company: {company_name}")

        user_message = f"""Question: {question}
Context: {', '.join(context_parts)}

Analyze this question and respond with JSON."""

        messages = [
            Message(role="system", content=self.SYSTEM_PROMPT),
            Message(role="user", content=user_message)
        ]

        try:
            response = self.llm_client.chat(
                messages=messages,
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=1000
            )

            # Parse JSON response
            content = response.content.strip()

            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            parsed = json.loads(content)

            # Build CustomerContext
            ctx_data = parsed.get("customer_context", {})
            customer_context = CustomerContext(
                roles=ctx_data.get("roles", []),
                scale=ctx_data.get("scale"),
                timeline_months=ctx_data.get("timeline_months"),
                hours_per_week=ctx_data.get("hours_per_week"),
                skill_focus=ctx_data.get("skill_focus", []),
                hands_on_required=ctx_data.get("hands_on_required", False)
            )

            # Build RetrievalPlan
            plan_data = parsed.get("retrieval_plan", {})
            retrieval_plan = RetrievalPlan(
                use_catalog=plan_data.get("use_catalog", True),
                use_csv=plan_data.get("use_csv", True),
                top_k=plan_data.get("top_k", 5)
            )

            # Map task type
            task_type_str = parsed.get("task_type", "recommendation")
            task_type_map = {
                "catalog_discovery": TaskType.CATALOG_DISCOVERY,
                "recommendation": TaskType.RECOMMENDATION,
                "skill_validation": TaskType.SKILL_VALIDATION
            }
            task_type = task_type_map.get(task_type_str, TaskType.RECOMMENDATION)

            logger.info(
                f"LLM Router: task_type={task_type.value}, "
                f"reasoning={parsed.get('reasoning', 'N/A')}"
            )

            return RouterOutput(
                task_type=task_type,
                customer_context=customer_context,
                retrieval_plan=retrieval_plan,
                audience_persona=persona
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Fall back to default classification
            return self._default_output(question, persona)

        except Exception as e:
            logger.error(f"LLM Router error: {e}")
            return self._default_output(question, persona)

    def _default_output(
        self,
        question: str,
        persona: AudiencePersona
    ) -> RouterOutput:
        """Generate default output when LLM fails."""
        # Simple keyword-based fallback
        question_lower = question.lower()

        if any(kw in question_lower for kw in ["list", "show", "what do we offer", "available"]):
            task_type = TaskType.CATALOG_DISCOVERY
        elif any(kw in question_lower for kw in ["do we cover", "how deep", "prerequisite"]):
            task_type = TaskType.SKILL_VALIDATION
        else:
            task_type = TaskType.RECOMMENDATION

        return RouterOutput(
            task_type=task_type,
            customer_context=CustomerContext(),
            retrieval_plan=RetrievalPlan(use_catalog=True, use_csv=True, top_k=5),
            audience_persona=persona
        )
