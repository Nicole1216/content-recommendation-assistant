"""Skill Semantic Resolver for alias mapping, taxonomy, and fuzzy matching."""

import os
import yaml
from pathlib import Path
from typing import Optional
from rapidfuzz import fuzz, process
from schemas.semantic import SkillCandidate, SkillSemanticResult


class SkillSemanticResolver:
    """
    Resolves skill queries to canonical skills using:
    1. Alias mapping (synonyms)
    2. Taxonomy disambiguation (intent detection)
    3. Fuzzy matching (typos, variations)
    4. Optional embeddings (feature flag)
    """

    def __init__(
        self,
        aliases_path: Optional[str] = None,
        taxonomy_path: Optional[str] = None,
        skill_vocabulary: Optional[list[str]] = None,
    ):
        """
        Initialize semantic resolver.

        Args:
            aliases_path: Path to skills_aliases.yaml
            taxonomy_path: Path to skills_taxonomy.yaml
            skill_vocabulary: List of actual skills from CSV (for fuzzy matching)
        """
        # Default paths
        if aliases_path is None:
            base_path = Path(__file__).parent.parent
            aliases_path = base_path / "data" / "skills_aliases.yaml"

        if taxonomy_path is None:
            base_path = Path(__file__).parent.parent
            taxonomy_path = base_path / "data" / "skills_taxonomy.yaml"

        # Load configurations
        self.aliases = self._load_aliases(aliases_path)
        self.taxonomy = self._load_taxonomy(taxonomy_path)
        self.skill_vocabulary = skill_vocabulary or []

        # Feature flag for embeddings
        self.use_embeddings = os.environ.get("USE_EMBEDDINGS", "0") == "1"
        self.embedding_model = None

        if self.use_embeddings:
            self._init_embeddings()

    def _load_aliases(self, path: str) -> dict:
        """Load skill aliases from YAML."""
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}

    def _load_taxonomy(self, path: str) -> dict:
        """Load skill taxonomy from YAML."""
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}

    def _init_embeddings(self):
        """Initialize embedding model if available."""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            self.use_embeddings = False

    def resolve(self, query: str, context: Optional[str] = None) -> SkillSemanticResult:
        """
        Resolve query to canonical skills with intent detection.

        Args:
            query: User query string
            context: Optional context (full question text)

        Returns:
            SkillSemanticResult with normalized skills and intents
        """
        query_lower = query.lower()
        context_lower = (context or query).lower()

        candidates = []
        normalized_skills = []
        skill_intents = []
        query_expansions = []
        explanations = []

        # Step 1: Alias mapping
        alias_matches = self._match_aliases(query_lower)
        for canonical, score in alias_matches:
            candidates.append(SkillCandidate(
                skill=canonical,
                score=score,
                source="alias",
                canonical_skill=canonical
            ))
            if canonical not in normalized_skills:
                normalized_skills.append(canonical)
                explanations.append(f"Alias match: '{canonical}'")

        # Step 2: Taxonomy disambiguation
        if normalized_skills or query_lower:
            taxonomy_matches = self._match_taxonomy(context_lower, normalized_skills)
            for intent_key, intent_data, score in taxonomy_matches:
                candidates.append(SkillCandidate(
                    skill=intent_data.get("canonical_skill", ""),
                    score=score,
                    source="taxonomy",
                    canonical_skill=intent_data.get("canonical_skill"),
                    intent_label=intent_data.get("intent_label")
                ))
                if intent_key not in skill_intents:
                    skill_intents.append(intent_key)
                    explanations.append(
                        f"Intent detected: {intent_data.get('intent_label', intent_key)}"
                    )

                # Add preferred skills as expansions
                for pref_skill in intent_data.get("preferred_skills", []):
                    if pref_skill not in query_expansions:
                        query_expansions.append(pref_skill)

        # Step 3: Fuzzy matching
        if self.skill_vocabulary:
            fuzzy_matches = self._fuzzy_match(query, top_k=5)
            for skill, score in fuzzy_matches:
                # If we have no other matches, accept lower threshold
                # If we have matches, only accept very high fuzzy scores
                threshold = 0.7 if len(normalized_skills) == 0 else 0.9
                if score >= threshold:
                    candidates.append(SkillCandidate(
                        skill=skill,
                        score=score,
                        source="fuzzy"
                    ))
                    if len(normalized_skills) == 0:  # Only add if no other matches
                        normalized_skills.append(skill)
                        explanations.append(f"Fuzzy match: '{skill}' (score: {score:.2f})")

        # Step 4: Optional embedding matching
        if self.use_embeddings and self.embedding_model and len(normalized_skills) == 0:
            embedding_matches = self._embedding_match(query)
            for skill, score in embedding_matches:
                candidates.append(SkillCandidate(
                    skill=skill,
                    score=score,
                    source="embedding"
                ))
                if skill not in normalized_skills:
                    normalized_skills.append(skill)
                    explanations.append(f"Embedding match: '{skill}' (score: {score:.2f})")

        # Calculate overall confidence
        confidence = 0.0
        if candidates:
            confidence = max(c.score for c in candidates)

        # Build explanation
        why = "; ".join(explanations) if explanations else "No strong matches found"

        return SkillSemanticResult(
            normalized_skills=normalized_skills,
            skill_intents=skill_intents,
            query_expansions=query_expansions,
            confidence=confidence,
            why=why,
            candidates=candidates,
            original_query=query
        )

    def _match_aliases(self, query_lower: str) -> list[tuple[str, float]]:
        """
        Match query against skill aliases.

        Returns:
            List of (canonical_skill, score) tuples
        """
        matches = []

        for canonical_skill, aliases in self.aliases.items():
            for alias in aliases:
                alias_lower = alias.lower()
                if alias_lower in query_lower:
                    # Exact substring match gets high score
                    score = 0.95
                    # Boost if it's a word boundary match
                    if f" {alias_lower} " in f" {query_lower} " or \
                       query_lower.startswith(alias_lower) or \
                       query_lower.endswith(alias_lower):
                        score = 1.0
                    matches.append((canonical_skill, score))
                    break  # Only count once per canonical skill

        return matches

    def _match_taxonomy(
        self,
        context_lower: str,
        normalized_skills: list[str]
    ) -> list[tuple[str, dict, float]]:
        """
        Match context against taxonomy to detect intent.

        Returns:
            List of (intent_key, intent_data, score) tuples
        """
        matches = []

        # Normalize skills for comparison (case-insensitive)
        normalized_skills_lower = [s.lower() for s in normalized_skills]

        for intent_key, intent_data in self.taxonomy.items():
            canonical_skill = intent_data.get("canonical_skill", "")

            # Check if this intent applies to our normalized skills (case-insensitive)
            if normalized_skills and canonical_skill.lower() not in normalized_skills_lower:
                continue

            # Score based on context signals
            context_signals = intent_data.get("context_signals", [])
            avoid_signals = intent_data.get("avoid_signals", [])

            signal_score = 0
            for signal in context_signals:
                if signal.lower() in context_lower:
                    signal_score += 1

            # Penalize if avoid signals present
            for avoid in avoid_signals:
                if avoid.lower() in context_lower:
                    signal_score -= 0.5

            if signal_score > 0:
                # Normalize score
                score = min(signal_score / len(context_signals), 1.0)
                matches.append((intent_key, intent_data, score))

        # Sort by score
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches

    def _fuzzy_match(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """
        Fuzzy match query against skill vocabulary.

        Returns:
            List of (skill, score) tuples
        """
        if not self.skill_vocabulary:
            return []

        # Use rapidfuzz for fuzzy matching
        results = process.extract(
            query,
            self.skill_vocabulary,
            scorer=fuzz.WRatio,
            limit=top_k
        )

        # Convert scores from 0-100 to 0-1
        matches = [(skill, score / 100.0) for skill, score, _ in results]
        return matches

    def _embedding_match(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """
        Match query using embeddings (if enabled).

        Returns:
            List of (skill, score) tuples
        """
        if not self.use_embeddings or not self.embedding_model or not self.skill_vocabulary:
            return []

        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity

            # Encode query
            query_embedding = self.embedding_model.encode([query])

            # Encode skills
            skill_embeddings = self.embedding_model.encode(self.skill_vocabulary)

            # Calculate similarity
            similarities = cosine_similarity(query_embedding, skill_embeddings)[0]

            # Get top_k
            top_indices = np.argsort(similarities)[-top_k:][::-1]

            matches = [
                (self.skill_vocabulary[i], float(similarities[i]))
                for i in top_indices
            ]

            return matches

        except Exception:
            # If embeddings fail, return empty
            return []

    def set_skill_vocabulary(self, skills: list[str]):
        """Update skill vocabulary for fuzzy/embedding matching."""
        self.skill_vocabulary = skills
