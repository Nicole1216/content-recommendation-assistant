"""Tests for Critic Agent."""

import pytest
from agents.critic import CriticAgent
from schemas.context import MergedContext, TaskType, AudiencePersona, CustomerContext
from schemas.responses import ComposerOutput, CriticDecision


class TestCriticAgent:
    """Test Critic Agent validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.critic = CriticAgent()

    def test_critic_blocks_unsupported_claims(self):
        """Test that critic blocks responses with unsupported claims."""
        context = MergedContext(
            user_question="Test question",
            task_type=TaskType.RECOMMENDATION,
            audience_persona=AudiencePersona.CTO,
            customer_context=CustomerContext(),
            retrieved_evidence={}
        )

        # Response with unsupported claim and no citations
        output = ComposerOutput(
            response_text="We offer the best programs guaranteed to work.",
            citations=[],
            assumptions_and_gaps=[],
        )

        result = self.critic.critique(context, output)

        assert result.decision == CriticDecision.REVISE
        assert result.evidence_support_score < 0.7

    def test_critic_passes_well_cited_response(self):
        """Test that critic passes responses with proper citations."""
        context = MergedContext(
            user_question="Test question",
            task_type=TaskType.CATALOG_DISCOVERY,
            audience_persona=AudiencePersona.CTO,
            customer_context=CustomerContext(),
            retrieved_evidence={}
        )

        # Well-cited response
        output = ComposerOutput(
            response_text="We have 3 programs available for Python learning.",
            citations=["[Catalog: cd0000, AI Programming with Python]"],
            assumptions_and_gaps=[],
        )

        result = self.critic.critique(context, output)

        # Should have decent scores
        assert result.evidence_support_score >= 0.5

    def test_critic_checks_completeness_for_recommendations(self):
        """Test that critic checks completeness for recommendation tasks."""
        context = MergedContext(
            user_question="What should I recommend?",
            task_type=TaskType.RECOMMENDATION,
            audience_persona=AudiencePersona.CTO,
            customer_context=CustomerContext(),
            retrieved_evidence={}
        )

        # Incomplete response - no evaluation questions answered
        output = ComposerOutput(
            response_text="Here's a program.",
            citations=["[Catalog: cd0000]"],
            assumptions_and_gaps=[],
            evaluation_questions_answered={},  # Empty - incomplete
        )

        result = self.critic.critique(context, output)

        assert result.decision == CriticDecision.REVISE
        assert result.completeness_score < 0.7
        assert any("evaluation questions" in c.lower() for c in result.critique)

    def test_critic_checks_persona_fit_cto(self):
        """Test that critic checks persona fit for CTO."""
        context = MergedContext(
            user_question="Test question",
            task_type=TaskType.RECOMMENDATION,
            audience_persona=AudiencePersona.CTO,
            customer_context=CustomerContext(),
            retrieved_evidence={}
        )

        # Response without technical details for CTO
        output = ComposerOutput(
            response_text="This is a nice program for learning.",
            citations=["[Catalog: cd0000]"],
            assumptions_and_gaps=[],
            evaluation_questions_answered={
                "Do you cover this specific skill?": True,
                "How deep is the skill coverage?": True,
                "Is the skill taught hands-on?": True,
                "What tools/technologies are used?": True,
                "What prerequisites are assumed?": True,
                "How long to reach working proficiency?": True,
            }
        )

        result = self.critic.critique(context, output)

        # Should flag persona mismatch
        assert result.persona_fit_score < 1.0

    def test_critic_requires_assumptions_section(self):
        """Test that critic requires assumptions section for recommendations."""
        context = MergedContext(
            user_question="Test question",
            task_type=TaskType.RECOMMENDATION,
            audience_persona=AudiencePersona.CTO,
            customer_context=CustomerContext(),
            retrieved_evidence={}
        )

        # Response without assumptions section
        output = ComposerOutput(
            response_text="Tools: Not confirmed. Skills: Not confirmed.",
            citations=["[Catalog: cd0000]"],
            assumptions_and_gaps=[],  # Empty - should be flagged
            evaluation_questions_answered={
                "Do you cover this specific skill?": True,
                "How deep is the skill coverage?": True,
                "Is the skill taught hands-on?": True,
                "What tools/technologies are used?": True,
                "What prerequisites are assumed?": True,
                "How long to reach working proficiency?": True,
            }
        )

        result = self.critic.critique(context, output)

        assert any("assumptions" in c.lower() for c in result.critique)
