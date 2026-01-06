"""LLM-based critic agent for response validation."""

import json
import logging
from typing import Dict, Any

from llm.base_client import BaseLLMClient, Message
from schemas.context import MergedContext, AudiencePersona, TaskType
from schemas.responses import ComposerOutput, CriticOutput, CriticDecision

logger = logging.getLogger(__name__)


class LLMCriticAgent:
    """
    LLM-based critic for response quality validation.

    Evaluates responses on:
    - Evidence support (are claims backed by citations?)
    - Completeness (are key questions addressed?)
    - Persona fit (is tone appropriate for audience?)
    - Actionability (are next steps clear?)
    """

    SYSTEM_PROMPT = """You are a quality reviewer for sales enablement responses.
Your job is to evaluate if a response meets quality standards.

## Evaluation Criteria

### 1. Evidence Support (0.0 - 1.0)
- Are claims backed by cited program keys?
- Are specific numbers/durations from evidence?
- Are there unsupported assertions?

Score guide:
- 1.0: All claims have citations, no unsupported assertions
- 0.7: Most claims cited, minor unsupported claims
- 0.5: Mixed - some citations but several unsupported claims
- 0.3: Few citations, many unsupported claims
- 0.0: No citations, all claims unsupported

### 2. Completeness (0.0 - 1.0)
For recommendations, evaluate coverage of the 6 evaluation questions:
1. Skill coverage
2. Depth of coverage
3. Hands-on learning
4. Tools/technologies
5. Prerequisites
6. Time to proficiency

Score guide:
- 1.0: All relevant questions addressed thoroughly
- 0.7: Most questions addressed
- 0.5: Half addressed
- 0.3: Few addressed
- 0.0: None addressed

### 3. Persona Fit (0.0 - 1.0)
CTO audience should see: technical depth, tools, production readiness
HR audience should see: career outcomes, adoption, completion rates
L&D audience should see: pathways, implementation, measurement

Score guide:
- 1.0: Perfect match for audience
- 0.7: Good match, minor misses
- 0.5: Adequate but generic
- 0.3: Poor match, wrong emphasis
- 0.0: Completely wrong tone

### 4. Actionability
- Are next steps clear?
- Is the recommendation specific enough to act on?
- Are alternatives mentioned when appropriate?

## Decision Logic
- PASS: Average score >= 0.7 AND <= 2 critique items
- REVISE: Average score < 0.7 OR > 2 critique items

## Response Format
Respond with valid JSON only:
{
  "decision": "PASS" or "REVISE",
  "evidence_support_score": 0.0-1.0,
  "completeness_score": 0.0-1.0,
  "persona_fit_score": 0.0-1.0,
  "critique": ["specific issue 1", "specific issue 2"],
  "reasoning": "Brief explanation of decision"
}"""

    def __init__(self, llm_client: BaseLLMClient):
        """
        Initialize LLM critic.

        Args:
            llm_client: LLM client for evaluation
        """
        self.llm_client = llm_client

    def critique(
        self,
        context: MergedContext,
        composer_output: ComposerOutput,
        evidence: Dict[str, Any]
    ) -> CriticOutput:
        """
        Critique a composed response.

        Args:
            context: Original context
            composer_output: Response to evaluate
            evidence: Evidence that was available

        Returns:
            CriticOutput with decision and scores
        """
        # Build evaluation prompt
        user_prompt = self._build_evaluation_prompt(context, composer_output, evidence)

        messages = [
            Message(role="system", content=self.SYSTEM_PROMPT),
            Message(role="user", content=user_prompt)
        ]

        try:
            response = self.llm_client.chat(
                messages=messages,
                temperature=0.1,  # Low temperature for consistent evaluation
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

            # Build CriticOutput
            decision_str = parsed.get("decision", "REVISE")
            decision = CriticDecision.PASS if decision_str == "PASS" else CriticDecision.REVISE

            critique_items = parsed.get("critique", [])

            logger.info(
                f"LLM Critic: decision={decision.value}, "
                f"evidence={parsed.get('evidence_support_score', 0):.2f}, "
                f"completeness={parsed.get('completeness_score', 0):.2f}, "
                f"persona={parsed.get('persona_fit_score', 0):.2f}"
            )

            return CriticOutput(
                decision=decision,
                critique=critique_items,
                evidence_support_score=parsed.get("evidence_support_score", 0.5),
                completeness_score=parsed.get("completeness_score", 0.5),
                persona_fit_score=parsed.get("persona_fit_score", 0.5)
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse critic response as JSON: {e}")
            return self._default_output()

        except Exception as e:
            logger.error(f"LLM Critic error: {e}")
            return self._default_output()

    def _build_evaluation_prompt(
        self,
        context: MergedContext,
        composer_output: ComposerOutput,
        evidence: Dict[str, Any]
    ) -> str:
        """Build evaluation prompt."""
        parts = []

        # Original question
        parts.append(f"## Original Question\n{context.user_question}")

        # Context
        parts.append(f"## Task Type: {context.task_type.value}")
        parts.append(f"## Audience Persona: {context.audience_persona.value}")

        # Response to evaluate
        parts.append("## Response to Evaluate")
        response_text = composer_output.response_text
        if len(response_text) > 4000:
            response_text = response_text[:4000] + "\n... (truncated)"
        parts.append(response_text)

        # Citations found
        parts.append(f"## Citations in Response: {len(composer_output.citations)}")
        if composer_output.citations:
            parts.append(", ".join(composer_output.citations[:10]))

        # Assumptions noted
        if composer_output.assumptions_and_gaps:
            parts.append("## Assumptions/Gaps Noted")
            for item in composer_output.assumptions_and_gaps[:5]:
                parts.append(f"- {item}")

        # Available evidence summary
        parts.append("## Available Evidence Summary")
        evidence_keys = list(evidence.keys())[:5]
        parts.append(f"Evidence sources: {', '.join(evidence_keys)}")

        # Instructions
        parts.append("""
## Instructions
Evaluate this response and return JSON with:
- decision: "PASS" or "REVISE"
- evidence_support_score: 0.0-1.0
- completeness_score: 0.0-1.0
- persona_fit_score: 0.0-1.0
- critique: list of specific issues (if any)
- reasoning: brief explanation""")

        return "\n\n".join(parts)

    def _default_output(self) -> CriticOutput:
        """Return default output when LLM fails."""
        return CriticOutput(
            decision=CriticDecision.PASS,  # Don't block on failure
            critique=["Critic evaluation failed - auto-passing"],
            evidence_support_score=0.5,
            completeness_score=0.5,
            persona_fit_score=0.5
        )
