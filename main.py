#!/usr/bin/env python3
"""Sales Enablement Assistant CLI."""

import argparse
import sys
from config.settings import Settings
from schemas.context import AudiencePersona
from orchestrator import SalesEnablementOrchestrator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Sales Enablement Assistant - AI-powered sales support for Udacity Enterprise"
    )
    parser.add_argument(
        "--question",
        "-q",
        type=str,
        required=True,
        help="Seller question to process"
    )
    parser.add_argument(
        "--persona",
        "-p",
        type=str,
        choices=["CTO", "HR", "L&D"],
        default="CTO",
        help="Target audience persona (default: CTO)"
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        help="Path to CSV file (Phase 2: uses real CSV if provided, otherwise uses mock data)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results to retrieve (default: 5)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Map persona string to enum
    persona_map = {
        "CTO": AudiencePersona.CTO,
        "HR": AudiencePersona.HR,
        "L&D": AudiencePersona.L_AND_D,
    }
    persona = persona_map[args.persona]

    # Create settings
    settings = Settings(
        csv_path=args.csv_path,
        top_k=args.top_k,
        verbose=args.verbose,
    )

    # Initialize orchestrator
    orchestrator = SalesEnablementOrchestrator(settings=settings)

    # Process question
    try:
        response = orchestrator.process_question(args.question, persona)
        print("\n" + "="*60)
        print("FINAL RESPONSE")
        print("="*60 + "\n")
        print(response)
        print("\n")
    except Exception as e:
        print(f"Error processing question: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
