"""Main orchestrator for the Sales Enablement Assistant with LLM integration."""

import uuid
import logging
from typing import Optional, Dict, Any

from config.settings import Settings
from schemas.context import MergedContext, AudiencePersona
from schemas.responses import CriticDecision
from schemas.evidence import Evidence

# Data provider
from retrieval.real_csv_provider import RealCSVProvider

# LLM components
from llm.factory import create_llm_client, LLMProvider
from llm.base_client import BaseLLMClient

# Memory components
from memory.sqlite_store import SQLiteMemoryStore
from memory.context_manager import ConversationContextManager

# ReAct components
from react.tools import SearchProgramsTool, GetProgramDetailsTool, CompareProgramsTool
from react.loop import ReActLoop

# LLM-powered agents
from agents.llm_router import LLMRouterAgent
from agents.llm_composer import LLMComposerAgent
from agents.llm_critic import LLMCriticAgent

# Legacy agents (fallback)
from agents.router import RouterAgent
from agents.csv_details import CSVDetailsAgent
from agents.comparator import ComparatorAgent
from agents.composer import ComposerAgent
from agents.critic import CriticAgent

logger = logging.getLogger(__name__)


class SalesEnablementOrchestrator:
    """Main orchestrator with LLM-powered agents, memory, and ReAct loop."""

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize orchestrator.

        Args:
            settings: Application settings
        """
        self.settings = settings or Settings()

        # Initialize CSV provider
        logger.info(f"Using CSV data source: {self.settings.csv_path}")
        self.csv_provider = RealCSVProvider(
            csv_path=self.settings.csv_path,
            openai_api_key=self.settings.openai_api_key
        )

        # Initialize LLM client
        self.llm_client: Optional[BaseLLMClient] = None
        self._init_llm_client()

        # Initialize memory
        self.memory_store: Optional[SQLiteMemoryStore] = None
        self.context_manager: Optional[ConversationContextManager] = None
        if self.settings.memory_enabled:
            self._init_memory()

        # Initialize ReAct loop
        self.react_loop: Optional[ReActLoop] = None
        if self.settings.react_enabled and self.llm_client:
            self._init_react()

        # Initialize agents
        self._init_agents()

    def _init_llm_client(self):
        """Initialize LLM client based on settings."""
        api_key = self.settings.get_llm_api_key()

        if not api_key:
            logger.warning(
                f"No API key for {self.settings.llm_provider}. "
                "LLM features will be disabled, using rule-based fallback."
            )
            return

        try:
            provider = LLMProvider(self.settings.llm_provider)
            self.llm_client = create_llm_client(
                provider=provider,
                api_key=api_key,
                model=self.settings.llm_model
            )
            logger.info(
                f"LLM client initialized: {self.settings.llm_provider} "
                f"({self.llm_client.get_model_name()})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self.llm_client = None

    def _init_memory(self):
        """Initialize memory system."""
        try:
            self.memory_store = SQLiteMemoryStore(db_path=self.settings.db_path)
            self.context_manager = ConversationContextManager(
                store=self.memory_store,
                llm_client=self.llm_client
            )
            logger.info(f"Memory initialized: {self.settings.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize memory: {e}")
            self.memory_store = None
            self.context_manager = None

    def _init_react(self):
        """Initialize ReAct loop with tools."""
        tools = [
            SearchProgramsTool(self.csv_provider),
            GetProgramDetailsTool(self.csv_provider),
            CompareProgramsTool(self.csv_provider),
        ]
        self.react_loop = ReActLoop(
            llm_client=self.llm_client,
            tools=tools,
            max_iterations=self.settings.max_react_iterations
        )
        logger.info(f"ReAct loop initialized with {len(tools)} tools")

    def _init_agents(self):
        """Initialize agents (LLM or fallback)."""
        if self.llm_client:
            # LLM-powered agents
            self.router = LLMRouterAgent(self.llm_client)
            self.composer = LLMComposerAgent(self.llm_client)
            self.critic = LLMCriticAgent(self.llm_client)
            logger.info("Using LLM-powered agents")
        else:
            # Fallback to rule-based agents
            self.router = RouterAgent()
            self.composer = ComposerAgent()
            self.critic = CriticAgent()
            logger.info("Using rule-based agents (fallback)")

        # These agents don't have LLM versions
        self.csv_details = CSVDetailsAgent(self.csv_provider)
        self.comparator = ComparatorAgent()

    def process_question(
        self,
        question: str,
        persona: AudiencePersona,
        conversation_id: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> str:
        """
        Process a user question end-to-end.

        Args:
            question: User question
            persona: Audience persona (CTO, HR, L&D)
            conversation_id: Optional conversation ID for multi-turn
            company_name: Optional company name for context

        Returns:
            Final seller-facing response
        """
        if self.settings.verbose:
            print(f"\n{'='*60}")
            print(f"PROCESSING QUESTION: {question}")
            print(f"PERSONA: {persona.value}")
            if company_name:
                print(f"COMPANY: {company_name}")
            print(f"{'='*60}\n")

        # Handle conversation memory
        context_messages = []
        if self.settings.memory_enabled and self.memory_store:
            conversation_id = self._handle_memory_init(
                conversation_id, company_name, persona
            )
            # Add user message to memory
            self.memory_store.add_turn(conversation_id, "user", question)
            # Get context from previous turns
            if self.context_manager:
                context_messages = self.context_manager.get_context_messages(conversation_id)

        # Use ReAct loop if available
        if self.react_loop and self.llm_client:
            response = self._process_with_react(
                question=question,
                persona=persona,
                company_name=company_name,
                context_messages=context_messages,
                conversation_id=conversation_id
            )
        else:
            response = self._process_legacy(
                question=question,
                persona=persona,
                company_name=company_name
            )

        # Save response to memory
        if self.settings.memory_enabled and self.memory_store and conversation_id:
            self.memory_store.add_turn(conversation_id, "assistant", response)
            if self.context_manager:
                self.context_manager.maybe_summarize(conversation_id)

        return response

    def _handle_memory_init(
        self,
        conversation_id: Optional[str],
        company_name: Optional[str],
        persona: AudiencePersona
    ) -> str:
        """Initialize or validate conversation in memory."""
        if conversation_id:
            # Check if conversation exists
            existing = self.memory_store.get_conversation(conversation_id)
            if existing:
                return conversation_id

        # Create new conversation
        new_id = conversation_id or str(uuid.uuid4())
        self.memory_store.create_conversation(
            conversation_id=new_id,
            company_name=company_name,
            persona=persona.value
        )
        logger.info(f"Created new conversation: {new_id}")
        return new_id

    def _process_with_react(
        self,
        question: str,
        persona: AudiencePersona,
        company_name: Optional[str],
        context_messages: list,
        conversation_id: Optional[str]
    ) -> str:
        """Process question using ReAct loop."""
        if self.settings.verbose:
            print("Using ReAct loop for evidence gathering...")

        # Step 1: Route question
        if self.settings.verbose:
            print("\nSTEP 1: ROUTING (LLM)...")

        router_output = self.router.route(question, persona, company_name)

        if self.settings.verbose:
            print(f"  Task Type: {router_output.task_type.value}")

        # Step 2: Run ReAct loop
        if self.settings.verbose:
            print("\nSTEP 2: ReAct LOOP...")

        react_result = self.react_loop.run(
            question=question,
            context_messages=context_messages,
            persona=persona.value,
            company_name=company_name
        )

        if self.settings.verbose:
            print(f"  Iterations used: {react_result.iterations_used}")
            print(f"  Tools called: {react_result.tools_called}")

        # Step 3: Compose with critique loop
        if self.settings.verbose:
            print("\nSTEP 3: COMPOSING WITH CRITIQUE LOOP...")

        # Build merged context
        merged_context = MergedContext(
            user_question=question,
            task_type=router_output.task_type,
            audience_persona=persona,
            customer_context=router_output.customer_context,
            retrieved_evidence=react_result.evidence_gathered,
            conversation_id=conversation_id,
            company_name=company_name
        )

        # Compose with critique loop
        response = self._compose_with_critique(
            merged_context=merged_context,
            evidence=react_result.evidence_gathered
        )

        return response

    def _compose_with_critique(
        self,
        merged_context: MergedContext,
        evidence: Dict[str, Any]
    ) -> str:
        """Run compose-critique loop."""
        revision_count = 0
        critique_feedback = None

        while revision_count <= self.settings.max_revisions:
            # Compose
            if hasattr(self.composer, 'compose') and callable(getattr(self.composer, 'compose')):
                # LLM Composer
                if isinstance(self.composer, LLMComposerAgent):
                    composer_output = self.composer.compose(
                        context=merged_context,
                        evidence=evidence,
                        critique=critique_feedback
                    )
                else:
                    # Legacy composer
                    composer_output = self.composer.compose(merged_context, critique_feedback)
            else:
                logger.error("Composer does not have compose method")
                return "Error: Composer not properly initialized"

            if self.settings.verbose:
                print(f"  Draft {revision_count + 1} complete")

            # Critique
            if isinstance(self.critic, LLMCriticAgent):
                critic_output = self.critic.critique(
                    context=merged_context,
                    composer_output=composer_output,
                    evidence=evidence
                )
            else:
                critic_output = self.critic.critique(merged_context, composer_output)

            if self.settings.verbose:
                print(f"  Critic decision: {critic_output.decision.value}")
                print(f"  Scores: evidence={critic_output.evidence_support_score:.2f}, "
                      f"completeness={critic_output.completeness_score:.2f}, "
                      f"persona={critic_output.persona_fit_score:.2f}")

            if critic_output.decision == CriticDecision.PASS:
                if self.settings.verbose:
                    print("\nRESPONSE APPROVED")
                return self._format_final_output(composer_output, merged_context)

            # Revise
            if revision_count >= self.settings.max_revisions:
                if self.settings.verbose:
                    print(f"\nMAX REVISIONS REACHED ({self.settings.max_revisions})")
                return self._format_final_output(
                    composer_output,
                    merged_context,
                    critic_output.critique
                )

            critique_feedback = critic_output.critique
            revision_count += 1

            if self.settings.verbose:
                print(f"  Revising based on {len(critique_feedback)} critique items...")

        return self._format_final_output(composer_output, merged_context)

    def _process_legacy(
        self,
        question: str,
        persona: AudiencePersona,
        company_name: Optional[str]
    ) -> str:
        """Process question using legacy rule-based flow."""
        if self.settings.verbose:
            print("Using legacy rule-based processing...")

        # Step 1: Router
        router_output = self.router.route(question, persona)

        # Step 2: Gather evidence
        evidence = Evidence()
        top_k = router_output.retrieval_plan.top_k

        # Search programs
        csv_search_results = self.csv_provider.search_programs(question, top_k)

        # Convert to CatalogResult format
        from schemas.evidence import CatalogResult
        for result in csv_search_results:
            prog = result.program_entity
            catalog_result = CatalogResult(
                program_key=prog.program_key,
                program_title=prog.program_title,
                program_type=prog.program_type or "Course",
                summary=prog.program_summary or "",
                duration_hours=prog.program_duration_hours,
                difficulty_level=prog.difficulty_level,
                fit_score=result.relevance_score
            )
            evidence.catalog_results.append(catalog_result)

        # Get details
        if evidence.catalog_results:
            program_keys = [r.program_key for r in evidence.catalog_results]
            csv_output = self.csv_details.get_details(program_keys)
            evidence.csv_details = csv_output.results

            # Compare if multiple
            if len(evidence.csv_details) > 1:
                comparator_output = self.comparator.compare_multiple(evidence.csv_details)
                evidence.comparisons = comparator_output.results

        # Create merged context
        merged_context = MergedContext(
            user_question=question,
            task_type=router_output.task_type,
            audience_persona=persona,
            customer_context=router_output.customer_context,
            retrieved_evidence={
                "catalog_results": evidence.catalog_results,
                "csv_details": evidence.csv_details,
                "comparisons": evidence.comparisons,
            },
            company_name=company_name
        )

        # Compose with critique
        return self._compose_with_critique(
            merged_context=merged_context,
            evidence=merged_context.retrieved_evidence
        )

    def _format_final_output(
        self,
        composer_output,
        context: MergedContext,
        critique: Optional[list] = None
    ) -> str:
        """Format final output for display."""
        parts = [composer_output.response_text]

        # Add assumptions and gaps
        if composer_output.assumptions_and_gaps:
            parts.append("\n## Assumptions & Gaps")
            for item in composer_output.assumptions_and_gaps:
                parts.append(f"- {item}")

        # Add citations
        if composer_output.citations:
            parts.append("\n## Evidence Sources")
            for citation in composer_output.citations:
                parts.append(f"- {citation}")

        # Add critique if present (when max revisions reached)
        if critique:
            parts.append("\n## Reviewer Notes")
            parts.append("*The following items need attention:*")
            for item in critique:
                parts.append(f"- {item}")

        return "\n".join(parts)

    def get_conversation_history(self, conversation_id: str) -> Optional[list]:
        """Get conversation history for display."""
        if not self.memory_store:
            return None

        conversation = self.memory_store.get_conversation(conversation_id)
        if not conversation:
            return None

        return [
            {"role": turn.role, "content": turn.content, "timestamp": turn.timestamp}
            for turn in conversation.turns
        ]


# Alias for backward compatibility
Orchestrator = SalesEnablementOrchestrator
