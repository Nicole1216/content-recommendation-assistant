"""ReAct loop implementation."""

import json
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from llm.base_client import BaseLLMClient, Message
from .tools import Tool, ToolResult

logger = logging.getLogger(__name__)


class ReActStep(BaseModel):
    """A single step in the ReAct loop."""
    step_number: int
    thought: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None


class ReActResult(BaseModel):
    """Result of ReAct loop execution."""
    steps: List[ReActStep]
    final_answer: str
    iterations_used: int
    tools_called: List[str]
    evidence_gathered: Dict[str, Any]  # Collected evidence from tools


class ReActLoop:
    """
    ReAct (Reasoning + Acting) loop for iterative problem solving.

    The LLM reasons about what information it needs, calls tools to gather
    evidence, and iterates until it has enough information to answer.
    """

    MAX_ITERATIONS = 5

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tools: List[Tool],
        max_iterations: int = 5
    ):
        """
        Initialize ReAct loop.

        Args:
            llm_client: LLM client for reasoning
            tools: List of available tools
            max_iterations: Maximum iterations (default: 5)
        """
        self.llm_client = llm_client
        self.tools = {tool.name: tool for tool in tools}
        self.max_iterations = max_iterations
        self.tool_definitions = [tool.get_definition() for tool in tools]

    def run(
        self,
        question: str,
        context_messages: List[Message],
        persona: str,
        company_name: Optional[str] = None
    ) -> ReActResult:
        """
        Run ReAct loop until answer or max iterations.

        Args:
            question: User's question
            context_messages: Previous conversation context
            persona: Audience persona (CTO, HR, L&D)
            company_name: Optional company name

        Returns:
            ReActResult with steps, answer, and evidence
        """
        steps = []
        evidence_gathered = {}
        tools_called = []

        # Build initial messages
        messages = self._build_initial_messages(
            question=question,
            context_messages=context_messages,
            persona=persona,
            company_name=company_name
        )

        for iteration in range(self.max_iterations):
            logger.info(f"ReAct iteration {iteration + 1}/{self.max_iterations}")

            # Call LLM with tools
            response = self.llm_client.chat(
                messages=messages,
                tools=self.tool_definitions,
                temperature=0.3,
                max_tokens=4000
            )

            # Check if LLM wants to call tools
            if response.tool_calls:
                # First, add the assistant message with tool_calls (required by OpenAI)
                # We need to reconstruct this for the message history
                assistant_content = response.content or ""
                messages.append(Message(
                    role="assistant",
                    content=assistant_content,
                    tool_calls=response.tool_calls  # Include tool calls in assistant message
                ))

                # Now execute each tool and add tool response messages
                for tool_call in response.tool_calls:
                    tool_name = tool_call.name
                    tool_args = tool_call.arguments

                    step = ReActStep(
                        step_number=iteration + 1,
                        thought=f"Need to gather information using {tool_name}",
                        action=tool_name,
                        action_input=tool_args
                    )

                    # Execute tool
                    if tool_name in self.tools:
                        result = self.tools[tool_name].execute(**tool_args)
                        step.observation = self._format_observation(result)

                        # Store evidence
                        if result.success:
                            evidence_key = f"{tool_name}_{len(evidence_gathered)}"
                            evidence_gathered[evidence_key] = result.result
                            tools_called.append(tool_name)
                    else:
                        step.observation = f"Error: Unknown tool '{tool_name}'"

                    steps.append(step)

                    # Add tool result to messages
                    messages.append(Message(
                        role="tool",
                        content=step.observation,
                        tool_call_id=tool_call.id
                    ))

            else:
                # No tool call - LLM is ready to provide final answer
                logger.info(f"ReAct completed in {iteration + 1} iterations")

                return ReActResult(
                    steps=steps,
                    final_answer=response.content,
                    iterations_used=iteration + 1,
                    tools_called=tools_called,
                    evidence_gathered=evidence_gathered
                )

        # Max iterations reached - ask LLM for best answer with current evidence
        logger.warning("ReAct max iterations reached, generating final answer")

        final_prompt = Message(
            role="user",
            content="You've gathered enough information. Now provide your final answer based on the evidence collected."
        )
        messages.append(final_prompt)

        response = self.llm_client.chat(
            messages=messages,
            tools=None,  # No more tool calls
            temperature=0.5,
            max_tokens=4000
        )

        return ReActResult(
            steps=steps,
            final_answer=response.content,
            iterations_used=self.max_iterations,
            tools_called=tools_called,
            evidence_gathered=evidence_gathered
        )

    def _build_initial_messages(
        self,
        question: str,
        context_messages: List[Message],
        persona: str,
        company_name: Optional[str]
    ) -> List[Message]:
        """Build initial message list for ReAct loop."""
        messages = []

        # System prompt
        system_prompt = self._build_system_prompt(persona, company_name)
        messages.append(Message(role="system", content=system_prompt))

        # Add conversation context
        for msg in context_messages:
            if msg.role != "system":  # Skip system messages from context
                messages.append(msg)

        # Add current question
        messages.append(Message(role="user", content=question))

        return messages

    def _build_system_prompt(self, persona: str, company_name: Optional[str]) -> str:
        """Build persona-aware system prompt for ReAct."""
        base_prompt = """You are a Sales Enablement Assistant for Udacity Enterprise.
Your role is to help sellers answer questions about Udacity's programs and courses.

## Your Approach
1. First, think about what information you need to answer the question
2. Use the available tools to search for programs and gather evidence
3. Once you have enough information, provide a comprehensive answer

## Available Tools
- search_programs: Find programs matching a query (skills, roles, topics)
- get_program_details: Get detailed info about specific programs
- compare_programs: Compare multiple programs

## Guidelines
- Always gather evidence before making claims
- Cite program keys when referencing specific programs
- Acknowledge gaps if information is not available
- Be specific and actionable in your recommendations
- Match your communication style to the audience persona"""

        persona_instructions = {
            "CTO": """

## Audience: CTO
- Emphasize technical depth and real-world applicability
- Focus on tools, technologies, and hands-on projects
- Discuss how skills translate to production work
- Include technical prerequisites and stack details""",

            "HR": """

## Audience: HR Leadership
- Emphasize career outcomes and talent development
- Focus on role alignment and skill gaps addressed
- Discuss adoption metrics and completion expectations
- Include ROI considerations and business impact""",

            "L&D": """

## Audience: L&D Leadership
- Emphasize learning pathways and skill progression
- Focus on cohort-based implementation strategies
- Discuss measurement frameworks and assessments
- Include rollout recommendations and milestones"""
        }

        prompt = base_prompt + persona_instructions.get(persona, "")

        if company_name:
            prompt += f"\n\n## Context\nYou are helping prepare a proposal for {company_name}."

        return prompt

    def _format_observation(self, result: ToolResult) -> str:
        """Format tool result for LLM consumption."""
        if not result.success:
            return f"Error: {result.error}"

        # Truncate large results
        result_str = json.dumps(result.result, indent=2)
        if len(result_str) > 3000:
            result_str = result_str[:3000] + "\n... (truncated)"

        return result_str
