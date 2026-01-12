"""Script to index Udacity programs into Azure AI Search."""

import hashlib
import logging
import os
import sys
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from retrieval.azure.search_client import AzureSearchClient
from retrieval.azure.index_schema import create_index_schema

logger = logging.getLogger(__name__)


class AzureIndexer:
    """Indexes Udacity program data into Azure AI Search."""

    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        index_name: str = "udacity-programs"
    ):
        """
        Initialize indexer.

        Args:
            azure_endpoint: Azure Search endpoint
            azure_api_key: Azure Search admin key
            openai_api_key: OpenAI API key for embeddings
            index_name: Name of the search index
        """
        self.search_client = AzureSearchClient(
            endpoint=azure_endpoint,
            api_key=azure_api_key,
            index_name=index_name
        )
        self.index_name = index_name

        # OpenAI client for embeddings
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.openai_client = None

        if self.openai_api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized for embeddings")
            except ImportError:
                logger.error("OpenAI package not installed")

    def create_index(self) -> bool:
        """Create the search index with optimized schema."""
        schema = create_index_schema(self.index_name)
        return self.search_client.create_index(schema)

    def _embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        if not self.openai_client:
            return None

        try:
            response = self.openai_client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def _embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        if not self.openai_client:
            return []

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                response = self.openai_client.embeddings.create(
                    model=self.EMBEDDING_MODEL,
                    input=batch
                )
                for item in response.data:
                    all_embeddings.append(item.embedding)

                logger.info(f"Embedded {len(all_embeddings)}/{len(texts)} texts")

            except Exception as e:
                logger.error(f"Error embedding batch: {e}")
                # Fill with empty embeddings
                for _ in batch:
                    all_embeddings.append([0.0] * self.EMBEDDING_DIMENSIONS)

        return all_embeddings

    def load_csv_data(self, csv_path: str) -> pd.DataFrame:
        """Load program data from CSV."""
        logger.info(f"Loading CSV from {csv_path}")

        # Try different encodings
        for encoding in ["utf-16", "utf-8", "latin-1"]:
            try:
                df = pd.read_csv(csv_path, encoding=encoding, sep="\t")
                logger.info(f"Loaded {len(df)} rows with encoding {encoding}")
                return df
            except Exception:
                continue

        raise ValueError(f"Could not load CSV file: {csv_path}")

    def prepare_documents(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Prepare documents for indexing.

        Args:
            df: DataFrame with program data

        Returns:
            List of documents ready for indexing
        """
        documents = []

        # Column mapping (from CSV columns to index fields)
        column_map = {
            "Program Key": "program_key",
            "CD Key": "course_key",
            "Program Title": "program_title",
            "Course Title": "course_title",
            "Course Summary": "course_summary",
            "Skills": "skills",
            "Skill Subjects": "skill_subjects",
            "Skill Domains": "skill_domains",
            "Program Type": "program_type",
            "Difficulty Level New": "difficulty_level",
            "Program Duration Hours ": "duration_hours",
            "Course Prerequisite Skills": "prerequisites",
            "Software Requirements": "software_requirements",
            "Project Name.": "projects"
        }

        # Generate embeddings for skills
        logger.info("Generating embeddings for skills...")
        skills_texts = df["Skills"].fillna("").astype(str).tolist()
        embeddings = self._embed_batch(skills_texts)

        for idx, row in df.iterrows():
            # Generate unique ID
            doc_id = hashlib.md5(
                f"{row.get('Program Key', '')}_{row.get('CD Key', '')}_{idx}".encode()
            ).hexdigest()

            doc = {"id": doc_id}

            # Map columns
            for csv_col, index_field in column_map.items():
                if csv_col in df.columns:
                    value = row.get(csv_col)

                    # Handle numeric field (duration_hours)
                    if index_field == "duration_hours":
                        if pd.isna(value) or value == "" or value is None:
                            value = 0.0
                        else:
                            try:
                                value = float(value)
                            except (ValueError, TypeError):
                                value = 0.0
                    else:
                        # Handle text fields
                        if pd.isna(value) or value is None:
                            value = ""
                        else:
                            value = str(value)

                    doc[index_field] = value

            # Add embedding
            if idx < len(embeddings):
                doc["skills_vector"] = embeddings[idx]
            else:
                doc["skills_vector"] = [0.0] * self.EMBEDDING_DIMENSIONS

            documents.append(doc)

        logger.info(f"Prepared {len(documents)} documents")
        return documents

    def index_data(self, csv_path: str) -> bool:
        """
        Full indexing pipeline.

        Args:
            csv_path: Path to CSV file

        Returns:
            True if successful
        """
        # Step 1: Create index
        logger.info("Step 1: Creating index...")
        if not self.create_index():
            logger.error("Failed to create index")
            return False

        # Step 2: Load data
        logger.info("Step 2: Loading CSV data...")
        df = self.load_csv_data(csv_path)

        # Step 3: Prepare documents with embeddings
        logger.info("Step 3: Preparing documents with embeddings...")
        documents = self.prepare_documents(df)

        # Step 4: Upload documents
        logger.info("Step 4: Uploading documents to Azure Search...")
        if not self.search_client.upload_documents(documents):
            logger.error("Failed to upload documents")
            return False

        # Step 5: Get stats
        logger.info("Step 5: Getting index stats...")
        stats = self.search_client.get_index_stats()
        if stats:
            storage_mb = stats.get("storageSize", 0) / 1024 / 1024
            doc_count = stats.get("documentCount", 0)
            logger.info(f"Index stats: {doc_count} documents, {storage_mb:.2f} MB storage")

        logger.info("Indexing completed successfully!")
        return True


def main():
    """Run indexing from command line."""
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Index Udacity programs into Azure AI Search")
    parser.add_argument("--csv", default="data/Udacity_Content_Catalog_Skill.csv", help="Path to CSV file")
    parser.add_argument("--index", default="udacity-programs", help="Index name")
    parser.add_argument("--endpoint", help="Azure Search endpoint")
    parser.add_argument("--api-key", help="Azure Search admin API key")
    parser.add_argument("--openai-key", help="OpenAI API key")

    args = parser.parse_args()

    indexer = AzureIndexer(
        azure_endpoint=args.endpoint,
        azure_api_key=args.api_key,
        openai_api_key=args.openai_key,
        index_name=args.index
    )

    success = indexer.index_data(args.csv)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
