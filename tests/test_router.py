"""Tests for Router Agent."""

import pytest
from agents.router import RouterAgent
from schemas.context import TaskType, AudiencePersona


class TestRouterAgent:
    """Test Router Agent classification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.router = RouterAgent()

    def test_catalog_discovery_classification(self):
        """Test catalog discovery questions are classified correctly."""
        questions = [
            "Do we have GenAI content?",
            "Does Udacity offer Python courses?",
            "What programs are available for data science?",
        ]

        for question in questions:
            result = self.router.route(question, AudiencePersona.CTO)
            assert result.task_type == TaskType.CATALOG_DISCOVERY

    def test_recommendation_classification(self):
        """Test recommendation questions are classified correctly."""
        questions = [
            "What should I recommend for upskilling 200 data analysts?",
            "Customer wants to train their team in AI",
            "Client needs machine learning skills in 6 months",
        ]

        for question in questions:
            result = self.router.route(question, AudiencePersona.CTO)
            assert result.task_type == TaskType.RECOMMENDATION

    def test_skill_validation_classification(self):
        """Test skill validation questions are classified correctly."""
        questions = [
            "Do you cover Python hands-on?",
            "How deep is the GenAI coverage?",
            "What tools are used for data analysis?",
        ]

        for question in questions:
            result = self.router.route(question, AudiencePersona.CTO)
            assert result.task_type == TaskType.SKILL_VALIDATION

    def test_context_extraction_scale(self):
        """Test extraction of learner scale."""
        question = "We need to train 200 employees in Python"
        result = self.router.route(question, AudiencePersona.HR)

        assert result.customer_context.scale == 200

    def test_context_extraction_timeline(self):
        """Test extraction of timeline."""
        question = "Can we upskill our team in 6 months?"
        result = self.router.route(question, AudiencePersona.HR)

        assert result.customer_context.timeline_months == 6

    def test_context_extraction_skills(self):
        """Test extraction of skill focus."""
        question = "We need GenAI and Python training"
        result = self.router.route(question, AudiencePersona.CTO)

        assert "genai" in result.customer_context.skill_focus
        assert "python" in result.customer_context.skill_focus

    def test_retrieval_plan_discovery(self):
        """Test retrieval plan for discovery task."""
        question = "Do we have AI courses?"
        result = self.router.route(question, AudiencePersona.CTO)

        assert result.retrieval_plan.use_catalog is True
        assert result.retrieval_plan.use_csv is False

    def test_retrieval_plan_recommendation(self):
        """Test retrieval plan for recommendation task."""
        question = "What should I recommend for data analysts?"
        result = self.router.route(question, AudiencePersona.HR)

        assert result.retrieval_plan.use_catalog is True
        assert result.retrieval_plan.use_csv is True
