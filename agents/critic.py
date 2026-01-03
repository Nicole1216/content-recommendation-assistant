"""Critic Agent for validating responses."""

from schemas.context import MergedContext, TaskType
from schemas.responses import ComposerOutput, CriticOutput, CriticDecision
from agents.composer import ComposerAgent


class CriticAgent:
    """Validates composer output for quality and accuracy."""

    def __init__(self):
        """Initialize critic."""
        self.evaluation_questions = ComposerAgent.EVALUATION_QUESTIONS

    def critique(
        self,
        context: MergedContext,
        composer_output: ComposerOutput
    ) -> CriticOutput:
        """
        Critique composer output.

        Args:
            context: Merged context
            composer_output: Output from composer

        Returns:
            CriticOutput with decision and critique
        """
        critique_items = []

        # Check evidence support
        evidence_score = self._check_evidence_support(
            composer_output, context, critique_items
        )

        # Check completeness
        completeness_score = self._check_completeness(
            context, composer_output, critique_items
        )

        # Check persona fit
        persona_score = self._check_persona_fit(
            context, composer_output, critique_items
        )

        # Check actionability
        self._check_actionability(composer_output, critique_items)

        # Decide PASS or REVISE
        avg_score = (evidence_score + completeness_score + persona_score) / 3

        if avg_score >= 0.7 and len(critique_items) <= 2:
            decision = CriticDecision.PASS
        else:
            decision = CriticDecision.REVISE

        return CriticOutput(
            decision=decision,
            critique=critique_items,
            completeness_score=completeness_score,
            evidence_support_score=evidence_score,
            persona_fit_score=persona_score,
        )

    def _check_evidence_support(
        self,
        output: ComposerOutput,
        context: MergedContext,
        critique_items: list[str]
    ) -> float:
        """Check if claims are supported by evidence."""
        score = 1.0

        # Check if citations are present
        if not output.citations:
            critique_items.append(
                "No citations found - all claims must be backed by catalog or CSV evidence"
            )
            score -= 0.3

        # Check if response mentions specific data points
        response_lower = output.response_text.lower()

        # Look for unsupported claims
        unsupported_phrases = [
            "we offer", "udacity provides", "guaranteed", "proven to",
            "always", "never", "all programs", "every course"
        ]

        for phrase in unsupported_phrases:
            if phrase in response_lower:
                # Check if there's a citation nearby
                if phrase not in " ".join(output.citations).lower():
                    critique_items.append(
                        f"Potentially unsupported claim: '{phrase}' - verify with evidence"
                    )
                    score -= 0.1

        # Check assumptions are documented
        if "not confirmed" in response_lower and not output.assumptions_and_gaps:
            critique_items.append(
                "Response mentions unconfirmed information but no assumptions documented"
            )
            score -= 0.2

        return max(score, 0.0)

    def _check_completeness(
        self,
        context: MergedContext,
        output: ComposerOutput,
        critique_items: list[str]
    ) -> float:
        """Check if response is complete."""
        score = 1.0

        # For recommendation and skill_validation, check 6 questions
        if context.task_type in [TaskType.RECOMMENDATION, TaskType.SKILL_VALIDATION]:
            answered_count = sum(output.evaluation_questions_answered.values())
            total_questions = len(self.evaluation_questions)

            if answered_count < total_questions:
                missing = total_questions - answered_count
                critique_items.append(
                    f"Missing {missing} of {total_questions} evaluation questions"
                )
                score -= (missing / total_questions) * 0.5

            # Check for assumptions section
            if not output.assumptions_and_gaps:
                critique_items.append(
                    "No 'Assumptions & Gaps' section - must explicitly state what couldn't be confirmed"
                )
                score -= 0.2

        # For discovery, check if results are ranked
        if context.task_type == TaskType.CATALOG_DISCOVERY:
            if "relevance" not in output.response_text.lower() and "fit" not in output.response_text.lower():
                critique_items.append(
                    "Discovery results should include relevance/fit scores"
                )
                score -= 0.2

        return max(score, 0.0)

    def _check_persona_fit(
        self,
        context: MergedContext,
        output: ComposerOutput,
        critique_items: list[str]
    ) -> float:
        """Check if response is tailored to persona."""
        score = 1.0
        response_lower = output.response_text.lower()

        persona = context.audience_persona

        # CTO should see technical details
        if persona.value == "CTO":
            technical_terms = ["tools", "stack", "hands-on", "technical", "production"]
            found = sum(1 for term in technical_terms if term in response_lower)
            if found < 2:
                critique_items.append(
                    "CTO response should emphasize technical depth, tools, and production readiness"
                )
                score -= 0.3

        # HR should see role leveling and outcomes
        elif persona.value == "HR":
            hr_terms = ["role", "outcomes", "career", "adoption", "completion"]
            found = sum(1 for term in hr_terms if term in response_lower)
            if found < 2:
                critique_items.append(
                    "HR response should emphasize roles, outcomes, and adoption metrics"
                )
                score -= 0.3

        # L&D should see pathways and rollout
        elif persona.value == "L&D":
            ld_terms = ["pathway", "rollout", "cohort", "implementation", "measurement"]
            found = sum(1 for term in ld_terms if term in response_lower)
            if found < 2:
                critique_items.append(
                    "L&D response should emphasize learning pathways and implementation"
                )
                score -= 0.3

        return max(score, 0.0)

    def _check_actionability(
        self,
        output: ComposerOutput,
        critique_items: list[str]
    ) -> None:
        """Check if response is actionable for seller."""
        response_lower = output.response_text.lower()

        # Should have concrete recommendations
        if "recommend" not in response_lower and "suggest" not in response_lower:
            critique_items.append(
                "Response should include clear recommendations for the seller"
            )

        # Should not be too vague
        vague_phrases = ["might be good", "could work", "possibly", "maybe"]
        vague_count = sum(1 for phrase in vague_phrases if phrase in response_lower)
        if vague_count > 2:
            critique_items.append(
                "Response is too tentative - provide confident recommendations when evidence supports them"
            )
