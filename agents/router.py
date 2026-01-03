"""Router Agent for question classification and context extraction."""

import re
from schemas.context import TaskType, CustomerContext, AudiencePersona
from schemas.responses import RouterOutput, RetrievalPlan


class RouterAgent:
    """Routes questions and extracts context."""

    def __init__(self):
        """Initialize router with classification rules."""
        self.discovery_patterns = [
            r"do (we|you) have",
            r"does udacity (have|offer|provide)",
            r"is there (a|any)",
            r"what.*available",
            r"catalog",
            r"list.*programs",
        ]
        self.recommendation_patterns = [
            r"what should i (recommend|propose|suggest)",
            r"customer wants",
            r"client needs",
            r"looking for.*solution",
            r"upskill.*\d+",
            r"train.*team",
        ]
        self.skill_validation_patterns = [
            r"do (we|you) cover",
            r"how deep",
            r"what tools",
            r"prerequisites",
            r"hands.?on",
            r"time to proficiency",
        ]

    def route(self, question: str, persona: AudiencePersona) -> RouterOutput:
        """
        Route question and extract context.

        Args:
            question: User question
            persona: Target audience persona

        Returns:
            RouterOutput with task type, context, and retrieval plan
        """
        question_lower = question.lower()

        # Classify task type
        task_type = self._classify_task_type(question_lower)

        # Extract customer context
        customer_context = self._extract_customer_context(question_lower)

        # Create retrieval plan
        retrieval_plan = self._create_retrieval_plan(task_type, customer_context)

        return RouterOutput(
            task_type=task_type,
            customer_context=customer_context,
            retrieval_plan=retrieval_plan,
            audience_persona=persona,
        )

    def _classify_task_type(self, question_lower: str) -> TaskType:
        """Classify question into task type."""
        # Check patterns in priority order
        for pattern in self.skill_validation_patterns:
            if re.search(pattern, question_lower):
                return TaskType.SKILL_VALIDATION

        for pattern in self.recommendation_patterns:
            if re.search(pattern, question_lower):
                return TaskType.RECOMMENDATION

        for pattern in self.discovery_patterns:
            if re.search(pattern, question_lower):
                return TaskType.CATALOG_DISCOVERY

        # Default to catalog discovery
        return TaskType.CATALOG_DISCOVERY

    def _extract_customer_context(self, question_lower: str) -> CustomerContext:
        """Extract customer context from question."""
        context = CustomerContext()

        # Extract roles
        role_patterns = {
            "data analyst": r"data analyst",
            "product manager": r"product manager",
            "software engineer": r"software engineer",
            "business leader": r"business leader",
            "developer": r"developer",
        }
        for role, pattern in role_patterns.items():
            if re.search(pattern, question_lower):
                context.roles.append(role)

        # Extract scale (number of learners)
        scale_match = re.search(r"(\d+)\s*(people|learners|employees|users)", question_lower)
        if scale_match:
            context.scale = int(scale_match.group(1))

        # Extract timeline
        timeline_match = re.search(r"(\d+)\s*months?", question_lower)
        if timeline_match:
            context.timeline_months = int(timeline_match.group(1))

        # Extract hours per week
        hours_match = re.search(r"(\d+)\s*hours?[/\s]*week", question_lower)
        if hours_match:
            context.hours_per_week = int(hours_match.group(1))

        # Detect hands-on requirement
        if re.search(r"hands.?on|practical|project", question_lower):
            context.hands_on_required = True

        # Extract skill focus
        skill_keywords = [
            "genai", "generative ai", "python", "sql", "machine learning",
            "data analysis", "prompt engineering", "ai", "analytics"
        ]
        for skill in skill_keywords:
            if skill in question_lower:
                context.skill_focus.append(skill)

        # Detect technical vs non-technical
        if re.search(r"non.?technical|business|leader|manager", question_lower):
            context.audience_persona = "non-technical"
        elif re.search(r"technical|engineer|developer|analyst", question_lower):
            context.audience_persona = "technical"

        return context

    def _create_retrieval_plan(
        self,
        task_type: TaskType,
        customer_context: CustomerContext
    ) -> RetrievalPlan:
        """Create retrieval plan based on task type and context."""
        plan = RetrievalPlan()

        if task_type == TaskType.CATALOG_DISCOVERY:
            # Catalog only for discovery
            plan.use_catalog = True
            plan.use_csv = False
            plan.top_k = 5
            # Build catalog query from context
            query_parts = customer_context.skill_focus + customer_context.roles
            plan.catalog_query = " ".join(query_parts) if query_parts else "all programs"

        elif task_type == TaskType.RECOMMENDATION:
            # Use both catalog and CSV for recommendations
            plan.use_catalog = True
            plan.use_csv = True
            plan.top_k = 3
            query_parts = customer_context.skill_focus + customer_context.roles
            plan.catalog_query = " ".join(query_parts) if query_parts else "programs"

        elif task_type == TaskType.SKILL_VALIDATION:
            # Primarily CSV for detailed validation
            plan.use_catalog = True
            plan.use_csv = True
            plan.top_k = 3
            query_parts = customer_context.skill_focus
            plan.catalog_query = " ".join(query_parts) if query_parts else "skills"

        return plan
