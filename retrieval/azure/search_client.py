"""Azure AI Search client wrapper."""

import logging
import os
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)


class AzureSearchClient:
    """Client for Azure AI Search operations."""

    API_VERSION = "2024-07-01"

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        index_name: str = "udacity-programs"
    ):
        """
        Initialize Azure Search client.

        Args:
            endpoint: Azure Search endpoint URL
            api_key: Azure Search admin API key
            index_name: Name of the search index
        """
        self.endpoint = endpoint or os.environ.get("AZURE_SEARCH_ENDPOINT")
        self.api_key = api_key or os.environ.get("AZURE_SEARCH_API_KEY")
        self.index_name = index_name

        if not self.endpoint or not self.api_key:
            logger.warning("Azure Search credentials not provided")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }

    def _get_url(self, path: str) -> str:
        """Build full URL for API request."""
        base = self.endpoint.rstrip("/")
        return f"{base}/{path}?api-version={self.API_VERSION}"

    def is_available(self) -> bool:
        """Check if Azure Search is configured and available."""
        if not self.endpoint or not self.api_key:
            return False

        try:
            url = self._get_url(f"indexes/{self.index_name}")
            response = requests.get(url, headers=self._get_headers(), timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Azure Search availability check failed: {e}")
            return False

    def create_index(self, schema: Dict[str, Any]) -> bool:
        """
        Create or update search index.

        Args:
            schema: Index schema dictionary

        Returns:
            True if successful
        """
        try:
            url = self._get_url(f"indexes/{self.index_name}")
            response = requests.put(
                url,
                headers=self._get_headers(),
                json=schema,
                timeout=30
            )

            if response.status_code in [200, 201]:
                logger.info(f"Index '{self.index_name}' created/updated successfully")
                return True
            else:
                logger.error(f"Failed to create index: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return False

    def delete_index(self) -> bool:
        """Delete the search index."""
        try:
            url = self._get_url(f"indexes/{self.index_name}")
            response = requests.delete(url, headers=self._get_headers(), timeout=30)

            if response.status_code in [200, 204]:
                logger.info(f"Index '{self.index_name}' deleted")
                return True
            else:
                logger.error(f"Failed to delete index: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error deleting index: {e}")
            return False

    def upload_documents(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> bool:
        """
        Upload documents to the index.

        Args:
            documents: List of documents to upload
            batch_size: Number of documents per batch

        Returns:
            True if all documents uploaded successfully
        """
        url = self._get_url(f"indexes/{self.index_name}/docs/index")
        total = len(documents)
        success_count = 0

        for i in range(0, total, batch_size):
            batch = documents[i:i + batch_size]

            payload = {
                "value": [
                    {"@search.action": "mergeOrUpload", **doc}
                    for doc in batch
                ]
            }

            try:
                response = requests.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=60
                )

                if response.status_code in [200, 207]:
                    success_count += len(batch)
                    logger.info(f"Uploaded {success_count}/{total} documents")
                else:
                    logger.error(f"Batch upload failed: {response.status_code} - {response.text}")
                    return False

            except Exception as e:
                logger.error(f"Error uploading batch: {e}")
                return False

        logger.info(f"Successfully uploaded {success_count} documents")
        return True

    def vector_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: OData filter expression

        Returns:
            List of matching documents with scores
        """
        url = self._get_url(f"indexes/{self.index_name}/docs/search")

        payload = {
            "vectorQueries": [
                {
                    "kind": "vector",
                    "vector": query_vector,
                    "fields": "skills_vector",
                    "k": top_k
                }
            ],
            "select": "id,program_key,course_key,program_title,course_title,course_summary,skills,skill_subjects,skill_domains,program_type,difficulty_level,duration_hours,prerequisites,software_requirements,projects",
            "top": top_k
        }

        if filters:
            payload["filter"] = filters

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                results = response.json().get("value", [])
                return [
                    {
                        **{k: v for k, v in doc.items() if not k.startswith("@")},
                        "score": doc.get("@search.score", 0)
                    }
                    for doc in results
                ]
            else:
                logger.error(f"Vector search failed: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []

    def hybrid_search(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (vector + keyword).

        Args:
            query: Text query for keyword search
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: OData filter expression

        Returns:
            List of matching documents with scores
        """
        url = self._get_url(f"indexes/{self.index_name}/docs/search")

        payload = {
            "search": query,
            "searchFields": "program_title",
            "vectorQueries": [
                {
                    "kind": "vector",
                    "vector": query_vector,
                    "fields": "skills_vector",
                    "k": top_k
                }
            ],
            "select": "id,program_key,course_key,program_title,course_title,course_summary,skills,skill_subjects,skill_domains,program_type,difficulty_level,duration_hours,prerequisites,software_requirements,projects",
            "top": top_k
        }

        if filters:
            payload["filter"] = filters

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                results = response.json().get("value", [])
                return [
                    {
                        **{k: v for k, v in doc.items() if not k.startswith("@")},
                        "score": doc.get("@search.score", 0)
                    }
                    for doc in results
                ]
            else:
                logger.error(f"Hybrid search failed: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a single document by ID."""
        url = self._get_url(f"indexes/{self.index_name}/docs/{doc_id}")

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None

    def get_index_stats(self) -> Optional[Dict[str, Any]]:
        """Get index statistics including storage size."""
        try:
            url = self._get_url(f"indexes/{self.index_name}/stats")
            response = requests.get(url, headers=self._get_headers(), timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return None
