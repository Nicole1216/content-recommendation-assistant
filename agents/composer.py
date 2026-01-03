"""Composer Agent for writing seller-facing responses."""

from typing import Optional
from schemas.context import MergedContext, TaskType, AudiencePersona
from schemas.responses import ComposerOutput
from schemas.evidence import CatalogResult, CSVDetail, Comparison


class ComposerAgent:
    """Composes final seller-facing responses."""

    # 6 evaluation questions
    EVALUATION_QUESTIONS = [
        "Do you cover this specific skill?",
        "How deep is the skill coverage?",
        "Is the skill taught hands-on?",
        "What tools/technologies are used?",
        "What prerequisites are assumed?",
        "How long to reach working proficiency?",
    ]

    def compose(
        self,
        context: MergedContext,
        critique: Optional[list[str]] = None
    ) -> ComposerOutput:
        """
        Compose final response tailored to persona.

        Args:
            context: Merged context with evidence
            critique: Optional critique from previous revision

        Returns:
            ComposerOutput with response text and metadata
        """
        if context.task_type == TaskType.CATALOG_DISCOVERY:
            return self._compose_discovery(context)
        elif context.task_type == TaskType.RECOMMENDATION:
            return self._compose_recommendation(context, critique)
        elif context.task_type == TaskType.SKILL_VALIDATION:
            return self._compose_skill_validation(context, critique)
        else:
            return ComposerOutput(
                response_text="Unable to process this question type.",
                assumptions_and_gaps=["Unknown task type"]
            )

    def _compose_discovery(self, context: MergedContext) -> ComposerOutput:
        """Compose discovery response."""
        catalog_results = context.retrieved_evidence.get("catalog_results", [])

        response_parts = []
        citations = []
        assumptions = []

        # Opening based on persona
        if context.audience_persona == AudiencePersona.CTO:
            response_parts.append("## Technical Programs Available\n")
        elif context.audience_persona == AudiencePersona.HR:
            response_parts.append("## Learning Programs Available\n")
        else:
            response_parts.append("## Udacity Programs Available\n")

        if not catalog_results:
            response_parts.append("No matching programs found in the catalog.\n")
            assumptions.append("Catalog search returned no results")
        else:
            response_parts.append(f"Found {len(catalog_results)} relevant programs:\n")

            for i, result in enumerate(catalog_results, 1):
                response_parts.append(f"\n### {i}. {result.program_title}")
                response_parts.append(f"- **Type**: {result.program_type}")
                response_parts.append(f"- **Duration**: {result.duration_hours} hours")
                response_parts.append(f"- **Level**: {result.difficulty_level}")
                response_parts.append(f"- **Summary**: {result.summary}")
                response_parts.append(f"- **Relevance**: {result.fit_score:.0%}\n")

                citations.append(
                    f"[Catalog: {result.program_key}, {result.program_title}]"
                )

        response_text = "\n".join(response_parts)

        return ComposerOutput(
            response_text=response_text,
            citations=citations,
            assumptions_and_gaps=assumptions,
        )

    def _compose_recommendation(
        self,
        context: MergedContext,
        critique: Optional[list[str]] = None
    ) -> ComposerOutput:
        """Compose recommendation response with 6 evaluation questions."""
        catalog_results = context.retrieved_evidence.get("catalog_results", [])
        csv_details = context.retrieved_evidence.get("csv_details", [])
        comparisons = context.retrieved_evidence.get("comparisons", [])

        response_parts = []
        citations = []
        assumptions = []
        eval_answered = {}

        # Persona-specific opening
        response_parts.append(self._get_persona_header(context.audience_persona))
        response_parts.append(f"\n**Question**: {context.user_question}\n")

        # Recommendation section
        response_parts.append("## Recommended Solution\n")

        if not catalog_results:
            response_parts.append("No programs found matching the requirements.\n")
            assumptions.append("No catalog results available")
            for q in self.EVALUATION_QUESTIONS:
                eval_answered[q] = False
        else:
            top_program = catalog_results[0]
            response_parts.append(f"**Program**: {top_program.program_title}\n")
            response_parts.append(f"{top_program.summary}\n")
            citations.append(f"[Catalog: {top_program.program_key}]")

            # Get CSV details for top program
            top_detail = None
            for detail in csv_details:
                if detail.program_key == top_program.program_key:
                    top_detail = detail
                    break

            # Answer 6 evaluation questions
            response_parts.append("\n## Evaluation Against Your Requirements\n")

            # Q1: Coverage
            eval_answered["Do you cover this specific skill?"] = True
            skills_text = ", ".join(top_detail.course_skills) if top_detail else "Not confirmed"
            response_parts.append(f"### 1. Skill Coverage")
            response_parts.append(f"**Skills taught**: {skills_text}")
            if top_detail:
                citations.append(f"[CSV: {top_detail.program_key}, Course Skills]")
            else:
                assumptions.append("Detailed skill coverage not confirmed from CSV")
            response_parts.append("")

            # Q2: Depth
            eval_answered["How deep is the skill coverage?"] = True
            if top_detail:
                depth_text = f"{top_detail.difficulty_level} level, {len(top_detail.lesson_titles)} lessons"
                response_parts.append(f"### 2. Depth of Coverage")
                response_parts.append(f"**Depth**: {depth_text}")
                response_parts.append(f"**Lessons**: {', '.join(top_detail.lesson_titles[:3])}{'...' if len(top_detail.lesson_titles) > 3 else ''}")
                citations.append(f"[CSV: {top_detail.program_key}, Lessons]")
            else:
                response_parts.append(f"### 2. Depth of Coverage")
                response_parts.append("**Depth**: Not confirmed from detailed curriculum")
                assumptions.append("Curriculum depth not available in CSV")
            response_parts.append("")

            # Q3: Hands-on
            eval_answered["Is the skill taught hands-on?"] = True
            if top_detail and top_detail.project_titles:
                response_parts.append(f"### 3. Hands-On Learning")
                response_parts.append(f"**Projects**: {len(top_detail.project_titles)} hands-on projects")
                response_parts.append(f"- {', '.join(top_detail.project_titles)}")
                citations.append(f"[CSV: {top_detail.program_key}, Projects]")
            else:
                response_parts.append(f"### 3. Hands-On Learning")
                response_parts.append("**Projects**: Not confirmed")
                assumptions.append("Project-based learning not confirmed from CSV")
            response_parts.append("")

            # Q4: Tools
            eval_answered["What tools/technologies are used?"] = True
            if top_detail and top_detail.third_party_tools:
                response_parts.append(f"### 4. Tools & Technologies")
                response_parts.append(f"**Tools**: {', '.join(top_detail.third_party_tools)}")
                if top_detail.software_requirements:
                    response_parts.append(f"**Software**: {', '.join(top_detail.software_requirements)}")
                citations.append(f"[CSV: {top_detail.program_key}, Tools]")
            else:
                response_parts.append(f"### 4. Tools & Technologies")
                response_parts.append("**Tools**: Not specified in available data")
                assumptions.append("Tool requirements not confirmed from CSV")
            response_parts.append("")

            # Q5: Prerequisites
            eval_answered["What prerequisites are assumed?"] = True
            if top_detail:
                prereq_text = ", ".join(top_detail.prerequisite_skills) if top_detail.prerequisite_skills else "None specified"
                response_parts.append(f"### 5. Prerequisites")
                response_parts.append(f"**Required**: {prereq_text}")
                citations.append(f"[CSV: {top_detail.program_key}, Prerequisites]")
            else:
                response_parts.append(f"### 5. Prerequisites")
                response_parts.append("**Required**: Not confirmed")
                assumptions.append("Prerequisites not confirmed from CSV")
            response_parts.append("")

            # Q6: Time to proficiency
            eval_answered["How long to reach working proficiency?"] = True
            if top_program.duration_hours:
                # Calculate based on customer context
                timeline_text = f"{top_program.duration_hours} hours total"
                if context.customer_context.hours_per_week:
                    weeks = top_program.duration_hours / context.customer_context.hours_per_week
                    timeline_text += f" ({weeks:.0f} weeks at {context.customer_context.hours_per_week} hours/week)"
                response_parts.append(f"### 6. Time to Proficiency")
                response_parts.append(f"**Timeline**: {timeline_text}")
                citations.append(f"[Catalog: {top_program.program_key}, Duration]")
            else:
                response_parts.append(f"### 6. Time to Proficiency")
                response_parts.append("**Timeline**: Not confirmed")
                assumptions.append("Duration not available")
            response_parts.append("")

            # Comparison if multiple programs
            if len(catalog_results) > 1 and comparisons:
                response_parts.append("\n## Alternative Options\n")
                for comp in comparisons:
                    alt_program = next((p for p in catalog_results if p.program_key == comp.program_b_key), None)
                    if alt_program:
                        response_parts.append(f"**Alternative**: {alt_program.program_title}")
                        response_parts.append(f"- Choose if: {', '.join(comp.choose_b_if)}")
                        citations.append(f"[Comparison: {comp.program_a_key} vs {comp.program_b_key}]")
                        response_parts.append("")

            # Persona-specific closing
            response_parts.append(self._get_persona_closing(context))

        response_text = "\n".join(response_parts)

        return ComposerOutput(
            response_text=response_text,
            citations=citations,
            assumptions_and_gaps=assumptions,
            evaluation_questions_answered=eval_answered,
        )

    def _compose_skill_validation(
        self,
        context: MergedContext,
        critique: Optional[list[str]] = None
    ) -> ComposerOutput:
        """Compose skill validation response."""
        # Similar to recommendation but focused on skill depth
        return self._compose_recommendation(context, critique)

    def _get_persona_header(self, persona: AudiencePersona) -> str:
        """Get persona-specific header."""
        if persona == AudiencePersona.CTO:
            return "## Technical Assessment for CTO"
        elif persona == AudiencePersona.HR:
            return "## Talent Development Recommendation for HR"
        else:
            return "## Learning Strategy for L&D"

    def _get_persona_closing(self, context: MergedContext) -> str:
        """Get persona-specific closing."""
        persona = context.audience_persona

        if persona == AudiencePersona.CTO:
            return (
                "\n## Technical Readiness\n"
                "This program provides production-ready skills with hands-on projects. "
                "Graduates can contribute to real projects immediately upon completion."
            )
        elif persona == AudiencePersona.HR:
            return (
                "\n## Adoption & Outcomes\n"
                "This program is designed for working professionals and includes career services. "
                "Completion rates and learner satisfaction are tracked via LMS."
            )
        else:
            return (
                "\n## Implementation Roadmap\n"
                "Recommend cohort-based rollout with quarterly milestones. "
                "Progress tracking and completion metrics available through admin dashboard."
            )
