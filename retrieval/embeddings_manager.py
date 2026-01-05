"""Embeddings manager for semantic search with auto-detection of CSV changes."""

import hashlib
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """Manages skill embeddings with caching and auto-detection of CSV changes."""

    CACHE_DIR = Path(".embeddings_cache")
    EMBEDDINGS_FILE = "skill_embeddings.pkl"
    METADATA_FILE = "embeddings_metadata.json"
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize embeddings manager.

        Args:
            openai_api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
        """
        self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.client = None
        self.skill_embeddings: dict[str, np.ndarray] = {}
        self.skills_list: list[str] = []

        # Ensure cache directory exists
        self.CACHE_DIR.mkdir(exist_ok=True)

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized for embeddings")
            except ImportError:
                logger.warning("OpenAI package not installed. Run: pip install openai")
        else:
            logger.warning("No OpenAI API key provided. Embeddings will be disabled.")

    def _compute_csv_hash(self, csv_path: str) -> str:
        """Compute hash of CSV file for change detection."""
        with open(csv_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _load_cached_metadata(self) -> Optional[dict]:
        """Load cached metadata if exists."""
        metadata_path = self.CACHE_DIR / self.METADATA_FILE
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                return json.load(f)
        return None

    def _save_metadata(self, csv_hash: str, skills_count: int):
        """Save metadata for cache validation."""
        metadata = {
            "csv_hash": csv_hash,
            "skills_count": skills_count,
            "model": self.EMBEDDING_MODEL,
        }
        with open(self.CACHE_DIR / self.METADATA_FILE, "w") as f:
            json.dump(metadata, f)

    def _load_cached_embeddings(self) -> bool:
        """Load cached embeddings if valid."""
        embeddings_path = self.CACHE_DIR / self.EMBEDDINGS_FILE
        if embeddings_path.exists():
            try:
                with open(embeddings_path, "rb") as f:
                    data = pickle.load(f)
                    self.skill_embeddings = data["embeddings"]
                    self.skills_list = data["skills_list"]
                logger.info(f"Loaded {len(self.skills_list)} cached embeddings")
                return True
            except Exception as e:
                logger.warning(f"Failed to load cached embeddings: {e}")
        return False

    def _save_embeddings(self):
        """Save embeddings to cache."""
        data = {
            "embeddings": self.skill_embeddings,
            "skills_list": self.skills_list,
        }
        with open(self.CACHE_DIR / self.EMBEDDINGS_FILE, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"Saved {len(self.skills_list)} embeddings to cache")

    def _embed_texts(self, texts: list[str], batch_size: int = 100) -> list[np.ndarray]:
        """Embed a list of texts using OpenAI API."""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.client.embeddings.create(
                    model=self.EMBEDDING_MODEL,
                    input=batch
                )
                for item in response.data:
                    all_embeddings.append(np.array(item.embedding))

                if i + batch_size < len(texts):
                    logger.info(f"Embedded {i + batch_size}/{len(texts)} skills...")

            except Exception as e:
                logger.error(f"Error embedding batch: {e}")
                raise

        return all_embeddings

    def initialize(self, csv_path: str, skills: list[str]) -> bool:
        """
        Initialize embeddings, using cache if CSV unchanged.

        Args:
            csv_path: Path to CSV file
            skills: List of unique skills from CSV

        Returns:
            True if embeddings are available, False otherwise
        """
        if not self.client:
            logger.warning("Embeddings disabled - no OpenAI API key")
            return False

        # Compute current CSV hash
        csv_hash = self._compute_csv_hash(csv_path)

        # Check if cache is valid
        metadata = self._load_cached_metadata()
        if metadata and metadata.get("csv_hash") == csv_hash:
            # CSV unchanged, try to load cache
            if self._load_cached_embeddings():
                logger.info("CSV unchanged - using cached embeddings")
                return True

        # Need to generate new embeddings
        logger.info(f"Generating embeddings for {len(skills)} skills...")

        # Filter out empty skills
        valid_skills = [s for s in skills if s and s.strip()]

        try:
            embeddings = self._embed_texts(valid_skills)

            # Store as dict for fast lookup
            self.skills_list = valid_skills
            self.skill_embeddings = {
                skill: emb for skill, emb in zip(valid_skills, embeddings)
            }

            # Save to cache
            self._save_embeddings()
            self._save_metadata(csv_hash, len(valid_skills))

            logger.info(f"Successfully generated {len(valid_skills)} embeddings")
            return True

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return False

    def embed_query(self, query: str) -> Optional[np.ndarray]:
        """Embed a search query."""
        if not self.client:
            return None

        try:
            response = self.client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=query
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            return None

    def find_similar_skills(
        self,
        query: str,
        top_k: int = 20,
        threshold: float = 0.3
    ) -> list[tuple[str, float]]:
        """
        Find skills semantically similar to the query.

        Args:
            query: Search query
            top_k: Number of similar skills to return
            threshold: Minimum similarity score (0-1)

        Returns:
            List of (skill, similarity_score) tuples
        """
        if not self.skill_embeddings:
            return []

        query_embedding = self.embed_query(query)
        if query_embedding is None:
            return []

        # Compute cosine similarity with all skills
        similarities = []
        for skill, skill_emb in self.skill_embeddings.items():
            # Cosine similarity
            similarity = np.dot(query_embedding, skill_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(skill_emb)
            )
            if similarity >= threshold:
                similarities.append((skill, float(similarity)))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def is_available(self) -> bool:
        """Check if embeddings are available."""
        return bool(self.skill_embeddings)
