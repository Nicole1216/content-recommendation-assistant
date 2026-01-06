"""LLM-based composer agent for persona-aware response generation."""

import json
import logging
from typing import Optional, List, Dict, Any

from llm.base_client import BaseLLMClient, Message
from schemas.context import MergedContext, AudiencePersona, TaskType
from schemas.responses import ComposerOutput

logger = logging.getLogger(__name__)


class LLMComposerAgent:
    """
    LLM-based response composer with persona awareness.

    Generates tailored responses for different audiences (CTO, HR, L&D)
    based on gathered evidence.
    """

    BASE_SYSTEM_PROMPT = """You are a Sales Enablement Assistant writing responses for Udacity sellers.
Your responses help sellers answer customer questions about training programs.

## Response Quality Standards
1. Only make claims supported by the evidence provided
2. Always cite program keys when referencing specific programs (e.g., [Program: nd104])
3. Acknowledge when information is not available
4. Be confident when evidence supports claims
5. Provide actionable next steps

## Structure Guidelines
- Start with a direct answer to the question
- Support claims with specific program details
- Include relevant metrics (duration, skill count, project count)
- End with clear recommendations or next steps

## Citation Format
Use this format for citations: [Program: program_key]
Example: "The Data Science Nanodegree [Program: nd025] covers machine learning fundamentals."

## Assumptions and Gaps
At the end of your response, include:
- **Assumptions**: What you assumed about the customer's needs
- **Information Gaps**: What information was not available in the evidence"""

    PERSONA_PROMPTS = {
        AudiencePersona.CTO: """
## Audience: Chief Technology Officer (CTO)

### Communication Style
- Lead with technical capabilities and architecture
- Be precise about tools, languages, and frameworks
- Discuss production readiness and real-world applicability
- Include specific project examples that demonstrate hands-on skills

### Key Points to Address
- Technical depth and rigor of content
- Tools and technologies covered
- Hands-on projects and their complexity
- Prerequisites and technical foundations required
- How skills translate to production environments

### Tone
- Professional and technically precise
- Confident but not overselling
- Focus on outcomes and capabilities""",

        AudiencePersona.HR: """
## Audience: HR Leadership

### Communication Style
- Lead with career outcomes and talent development value
- Emphasize role alignment and career progression
- Discuss adoption metrics and completion expectations
- Include business impact considerations

### Key Points to Address
- Career outcomes and role alignment
- Completion rates and learner engagement
- Skill development pathways
- Time investment and flexibility
- ROI indicators and business value

### Tone
- People-focused and outcomes-oriented
- Supportive and developmental
- Focus on talent and organizational growth""",

        AudiencePersona.L_AND_D: """
## Audience: Learning & Development (L&D) Leadership

### Communication Style
- Lead with learning pathways and skill progression
- Emphasize implementation strategies
- Discuss assessment and measurement frameworks
- Include cohort-based rollout recommendations

### Key Points to Address
- Learning pathway design
- Skill progression and prerequisites
- Assessment methods and certifications
- Cohort management options
- Progress tracking and reporting capabilities
- Integration with existing L&D systems

### Tone
- Educational and strategic
- Implementation-focused
- Emphasis on measurable outcomes"""
    }

    EVALUATION_QUESTIONS = [
        "Do you cover this specific skill?",
        "How deep is the skill coverage?",
        "Is the skill taught hands-on?",
        "What tools/technologies are used?",
        "What prerequisites are assumed?",
        "How long to reach working proficiency?",
    ]

    def __init__(self, llm_client: BaseLLMClient):
        """
        Initialize LLM composer.

        Args:
            llm_client: LLM client for generation
        """
        self.llm_client = llm_client

    def compose(
        self,
        context: MergedContext,
        evidence: Dict[str, Any],
        critique: Optional[List[str]] = None
    ) -> ComposerOutput:
        """
        Compose a response using LLM.

        Args:
            context: Merged context with question and metadata
            evidence: Evidence gathered from tools
            critique: Optional critique from previous iteration

        Returns:
            ComposerOutput with response and metadata
        """
        # Build system prompt with persona
        system_prompt = self._build_system_prompt(context.audience_persona, context.task_type)

        # Build user prompt with evidence and question
        user_prompt = self._build_user_prompt(context, evidence, critique)

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]

        try:
            response = self.llm_client.chat(
                messages=messages,
                temperature=0.5,  # Balanced creativity and consistency
                max_tokens=4000
            )

            # Parse response
            return self._parse_response(response.content, context)

        except Exception as e:
            logger.error(f"LLM Composer error: {e}")
            return ComposerOutput(
                response_text=f"Error generating response: {str(e)}",
                assumptions_and_gaps=["LLM generation failed"],
                citations=[]
            )

    def _build_system_prompt(self, persona: AudiencePersona, task_type: TaskType) -> str:
        """Build system prompt with persona instructions."""
        prompt = self.BASE_SYSTEM_PROMPT

        # Add persona-specific instructions
        persona_prompt = self.PERSONA_PROMPTS.get(persona, "")
        if persona_prompt:
            prompt += persona_prompt

        # Add task-specific instructions
        if task_type == TaskType.CATALOG_DISCOVERY:
            prompt += """

## Task: Catalog Discovery
The user wants to explore available programs. Provide:
- Overview of relevant programs found
- Brief highlights for each
- Comparison of options if multiple found"""

        elif task_type == TaskType.RECOMMENDATION:
            prompt += """

## Task: Recommendation
The user needs a specific recommendation. Provide:
- Clear recommendation with reasoning
- Address the 6 evaluation questions when relevant
- Include alternative options if appropriate"""

        elif task_type == TaskType.SKILL_VALIDATION:
            prompt += """

## Task: Skill Validation
The user wants to verify skill coverage. Provide:
- Direct answer about skill coverage
- Depth and hands-on nature of coverage
- Specific courses/programs that cover the skill"""

        return prompt

    def _build_user_prompt(
        self,
        context: MergedContext,
        evidence: Dict[str, Any],
        critique: Optional[List[str]]
    ) -> str:
        """Build user prompt with evidence and context."""
        parts = []

        # Question
        parts.append(f"## Question\n{context.user_question}")

        # Company context
        if context.customer_context:
            ctx = context.customer_context
            context_items = []
            if ctx.roles:
                context_items.append(f"Roles: {', '.join(ctx.roles)}")
            if ctx.scale:
                context_items.append(f"Scale: {ctx.scale} learners")
            if ctx.timeline_months:
                context_items.append(f"Timeline: {ctx.timeline_months} months")
            if ctx.skill_focus:
                context_items.append(f"Skill focus: {', '.join(ctx.skill_focus)}")
            if ctx.hours_per_week:
                context_items.append(f"Commitment: {ctx.hours_per_week} hrs/week")

            if context_items:
                parts.append(f"## Customer Context\n" + "\n".join(f"- {item}" for item in context_items))

        # Evidence
        parts.append("## Evidence from Search")
        evidence_str = json.dumps(evidence, indent=2, default=str)
        if len(evidence_str) > 8000:
            evidence_str = evidence_str[:8000] + "\n... (evidence truncated)"
        parts.append(evidence_str)

        # Critique feedback if revision
        if critique:
            parts.append("## Revision Feedback")
            parts.append("Please address these issues from the previous draft:")
            for item in critique:
                parts.append(f"- {item}")

        # Instructions
        parts.append("""
## Instructions
Write a comprehensive response that:
1. Directly answers the question
2. Cites specific program keys using [Program: key] format
3. Matches the communication style for the audience
4. Ends with Assumptions and Information Gaps sections""")

        return "\n\n".join(parts)

    def _parse_response(self, content: str, context: MergedContext) -> ComposerOutput:
        """Parse LLM response into ComposerOutput."""
        # Extract citations
        citations = []
        import re
        citation_pattern = r'\[Program:\s*([^\]]+)\]'
        matches = re.findall(citation_pattern, content)
        for match in matches:
            citations.append(f"[Program: {match.strip()}]")

        # Extract assumptions and gaps
        assumptions = []
        response_text = content

        # Try to extract assumptions section
        if "**Assumptions**" in content or "## Assumptions" in content:
            parts = re.split(r'\*\*Assumptions\*\*|## Assumptions', content)
            if len(parts) > 1:
                assumptions_section = parts[1]
                # Extract until next section
                if "**Information Gaps**" in assumptions_section or "## Information" in assumptions_section:
                    assumptions_section = re.split(r'\*\*Information|## Information', assumptions_section)[0]
                # Extract bullet points
                for line in assumptions_section.split('\n'):
                    line = line.strip()
                    if line.startswith('-') or line.startswith('*'):
                        assumptions.append(line[1:].strip())

        # Extract gaps
        gaps = []
        if "**Information Gaps**" in content or "## Information Gaps" in content:
            parts = re.split(r'\*\*Information Gaps\*\*|## Information Gaps', content)
            if len(parts) > 1:
                gaps_section = parts[1]
                for line in gaps_section.split('\n'):
                    line = line.strip()
                    if line.startswith('-') or line.startswith('*'):
                        gaps.append(line[1:].strip())

        # Combine assumptions and gaps
        all_assumptions = assumptions + gaps

        # Track which evaluation questions were addressed
        eval_questions_answered = {}
        content_lower = content.lower()
        for q in self.EVALUATION_QUESTIONS:
            # Simple heuristic - check if related keywords appear
            keywords = q.lower().split()[:3]
            eval_questions_answered[q] = any(kw in content_lower for kw in keywords)

        return ComposerOutput(
            response_text=response_text,
            citations=list(set(citations)),  # Deduplicate
            assumptions_and_gaps=all_assumptions if all_assumptions else ["No explicit assumptions noted"],
            evaluation_questions_answered=eval_questions_answered
        )
