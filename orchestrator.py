"""Main orchestrator for the Sales Enablement Assistant."""

import logging
from typing import Optional
from config.settings import Settings
from schemas.context import MergedContext, AudiencePersona
from schemas.responses import CriticDecision
from schemas.evidence import Evidence
from retrieval.real_csv_provider import RealCSVProvider
from agents.router import RouterAgent
from agents.csv_details import CSVDetailsAgent
from agents.comparator import ComparatorAgent
from agents.composer import ComposerAgent
from agents.critic import CriticAgent

logger = logging.getLogger(__name__)


class SalesEnablementOrchestrator:
    """Main orchestrator that coordinates all agents."""

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize orchestrator.

        Args:
            settings: Application settings
        """
        self.settings = settings or Settings()

        # Initialize CSV provider as the single data source
        logger.info(f"Using CSV data source: {self.settings.csv_path}")
        self.csv_provider = RealCSVProvider(csv_path=self.settings.csv_path)

        # Initialize agents
        self.router = RouterAgent()
        self.csv_details = CSVDetailsAgent(self.csv_provider)
        self.comparator = ComparatorAgent()
        self.composer = ComposerAgent()
        self.critic = CriticAgent()

    def process_question(
        self,
        question: str,
        persona: AudiencePersona
    ) -> str:
        """
        Process a user question end-to-end.

        Args:
            question: User question
            persona: Audience persona

        Returns:
            Final seller-facing response
        """
        if self.settings.verbose:
            print(f"\n{'='*60}")
            print(f"PROCESSING QUESTION: {question}")
            print(f"PERSONA: {persona.value}")
            print(f"{'='*60}\n")

        # Step 1: Router
        if self.settings.verbose:
            print("STEP 1: ROUTING...")
        router_output = self.router.route(question, persona)
        if self.settings.verbose:
            print(f"  Task Type: {router_output.task_type.value}")
            print(f"  Retrieval Plan: catalog={router_output.retrieval_plan.use_catalog}, "
                  f"csv={router_output.retrieval_plan.use_csv}")

        # Step 2: Search CSV for relevant programs
        if self.settings.verbose:
            print("\nSTEP 2: RETRIEVING EVIDENCE...")
        evidence = Evidence()

        top_k = router_output.retrieval_plan.top_k
        if self.settings.verbose:
            print("  Searching CSV data...")

        # Search programs using natural language query
        csv_search_results = self.csv_provider.search_programs(question, top_k)

        # Convert to CatalogResult format for compatibility
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

        if self.settings.verbose:
            print(f"  Found {len(evidence.catalog_results)} matching programs")

        # Get detailed CSV data for top results
        if evidence.catalog_results:
            # Get details for top results
            program_keys = [r.program_key for r in evidence.catalog_results]
            csv_output = self.csv_details.get_details(program_keys)
            evidence.csv_details = csv_output.results
            if self.settings.verbose:
                print(f"  CSV: {len(evidence.csv_details)} details retrieved")

            # Compare if multiple programs
            if len(evidence.csv_details) > 1:
                comparator_output = self.comparator.compare_multiple(evidence.csv_details)
                evidence.comparisons = comparator_output.results
                if self.settings.verbose:
                    print(f"  Comparisons: {len(evidence.comparisons)}")

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
            }
        )

        # Step 3: Composer (with revision loop)
        if self.settings.verbose:
            print("\nSTEP 3: COMPOSING RESPONSE...")

        revision_count = 0
        critique_feedback = None

        while revision_count <= self.settings.max_revisions:
            # Compose response
            composer_output = self.composer.compose(merged_context, critique_feedback)

            if self.settings.verbose:
                print(f"  Draft {revision_count + 1} complete")

            # Step 4: Critic review
            if self.settings.verbose:
                print(f"\nSTEP 4: CRITIC REVIEW (Attempt {revision_count + 1})...")

            critic_output = self.critic.critique(merged_context, composer_output)

            if self.settings.verbose:
                print(f"  Decision: {critic_output.decision.value}")
                print(f"  Evidence Score: {critic_output.evidence_support_score:.2f}")
                print(f"  Completeness Score: {critic_output.completeness_score:.2f}")
                print(f"  Persona Fit Score: {critic_output.persona_fit_score:.2f}")

            if critic_output.decision == CriticDecision.PASS:
                if self.settings.verbose:
                    print("\nFINAL RESPONSE APPROVED")
                return self._format_final_output(composer_output, merged_context)

            # REVISE needed
            if revision_count >= self.settings.max_revisions:
                if self.settings.verbose:
                    print(f"\nMAX REVISIONS REACHED ({self.settings.max_revisions})")
                    print("Returning best attempt with critique notes...")
                # Return with critique notes
                return self._format_final_output(
                    composer_output,
                    merged_context,
                    critic_output.critique
                )

            # Prepare for revision
            critique_feedback = critic_output.critique
            revision_count += 1

            if self.settings.verbose:
                print(f"\nRevising based on critique:")
                for item in critique_feedback:
                    print(f"  - {item}")

        return self._format_final_output(composer_output, merged_context)

    def _format_final_output(
        self,
        composer_output,
        context: MergedContext,
        critique: Optional[list[str]] = None
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

Orchestrator = SalesEnablementOrchestrator
