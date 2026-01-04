"""Catalog API provider for real Unified Catalog integration (Phase 3.5)."""

import logging
from typing import Optional
import requests
from schemas.evidence import CatalogResult

logger = logging.getLogger(__name__)


class CatalogAPIProvider:
    """
    Real Catalog API provider for discovery layer.

    Integrates with Udacity Unified Catalog API to answer:
    - "Do we have X?"
    - High-level existence & coverage

    Falls back gracefully if API is unavailable.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        auth_token: Optional[str] = None
    ):
        """
        Initialize Catalog API provider.

        Args:
            base_url: Base URL for the Unified Catalog API (e.g., https://api.udacity.com/api/unified-catalog)
            timeout: Request timeout in seconds (default: 10)
            auth_token: Optional authentication token
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.auth_token = auth_token
        self._is_available = True
        self._last_error: Optional[str] = None

    def _get_headers(self) -> dict:
        """Build request headers."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "Udacity-Sales-Enablement-Assistant/1.0"
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _handle_error(self, error: Exception, context: str) -> None:
        """
        Handle API errors and set availability flag.

        Args:
            error: Exception that occurred
            context: Context string for logging
        """
        self._is_available = False
        self._last_error = str(error)
        logger.warning(f"Catalog API error during {context}: {error}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[dict] = None
    ) -> list[CatalogResult]:
        """
        Search catalog via API.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional filters (e.g., program_type, difficulty_level)

        Returns:
            List of catalog results with fit scores
        """
        if not self._is_available:
            logger.warning(f"Catalog API unavailable (last error: {self._last_error}), returning empty results")
            return []

        try:
            # Build query parameters
            params = {
                "q": query,
                "limit": top_k
            }

            # Add filters if provided
            if filters:
                for key, value in filters.items():
                    params[key] = value

            # Make API request
            url = f"{self.base_url}/search"
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )

            # Handle authentication errors
            if response.status_code in (401, 403):
                self._handle_error(
                    Exception(f"Authentication failed: {response.status_code}"),
                    "search"
                )
                return []

            # Handle other errors
            if response.status_code != 200:
                self._handle_error(
                    Exception(f"API returned status {response.status_code}: {response.text}"),
                    "search"
                )
                return []

            # Parse response
            data = response.json()

            # Handle different response formats
            # Expected format: {"results": [...]} or direct array [...]
            if isinstance(data, dict):
                results = data.get("results", []) or data.get("programs", []) or data.get("data", [])
            elif isinstance(data, list):
                results = data
            else:
                logger.warning(f"Unexpected API response format: {type(data)}")
                return []

            # Convert to CatalogResult objects
            catalog_results = []
            for item in results[:top_k]:
                try:
                    catalog_result = self._parse_catalog_item(item)
                    if catalog_result:
                        catalog_results.append(catalog_result)
                except Exception as e:
                    logger.warning(f"Failed to parse catalog item: {e}")
                    continue

            return catalog_results

        except requests.exceptions.Timeout:
            self._handle_error(
                Exception(f"Request timeout after {self.timeout}s"),
                "search"
            )
            return []
        except requests.exceptions.ConnectionError as e:
            self._handle_error(e, "search")
            return []
        except Exception as e:
            self._handle_error(e, "search")
            return []

    def get_by_key(self, program_key: str) -> Optional[CatalogResult]:
        """
        Get a specific program by key.

        Args:
            program_key: Program key (e.g., "cd0101")

        Returns:
            CatalogResult if found, None otherwise
        """
        if not self._is_available:
            logger.warning(f"Catalog API unavailable (last error: {self._last_error}), returning None")
            return None

        try:
            # Make API request
            url = f"{self.base_url}/programs/{program_key}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )

            # Handle authentication errors
            if response.status_code in (401, 403):
                self._handle_error(
                    Exception(f"Authentication failed: {response.status_code}"),
                    "get_by_key"
                )
                return None

            # Handle not found
            if response.status_code == 404:
                return None

            # Handle other errors
            if response.status_code != 200:
                self._handle_error(
                    Exception(f"API returned status {response.status_code}: {response.text}"),
                    "get_by_key"
                )
                return None

            # Parse response
            data = response.json()

            # Handle different response formats
            if isinstance(data, dict) and "program" in data:
                item = data["program"]
            elif isinstance(data, dict):
                item = data
            else:
                logger.warning(f"Unexpected API response format: {type(data)}")
                return None

            return self._parse_catalog_item(item)

        except requests.exceptions.Timeout:
            self._handle_error(
                Exception(f"Request timeout after {self.timeout}s"),
                "get_by_key"
            )
            return None
        except requests.exceptions.ConnectionError as e:
            self._handle_error(e, "get_by_key")
            return None
        except Exception as e:
            self._handle_error(e, "get_by_key")
            return None

    def _parse_catalog_item(self, item: dict) -> Optional[CatalogResult]:
        """
        Parse API response item to CatalogResult.

        Args:
            item: API response item (dict)

        Returns:
            CatalogResult if parsing successful, None otherwise
        """
        try:
            # Map API fields to CatalogResult fields
            # Handle various field name conventions
            program_key = (
                item.get("program_key") or
                item.get("key") or
                item.get("id") or
                item.get("program_id") or
                ""
            )

            program_title = (
                item.get("program_title") or
                item.get("title") or
                item.get("name") or
                ""
            )

            program_type = (
                item.get("program_type") or
                item.get("type") or
                item.get("product_type") or
                "Course"
            )

            summary = (
                item.get("summary") or
                item.get("description") or
                item.get("overview") or
                ""
            )

            # Parse duration (may be in various formats)
            duration_hours = None
            if "duration_hours" in item:
                duration_hours = float(item["duration_hours"])
            elif "duration" in item:
                # Try to parse duration
                duration = item["duration"]
                if isinstance(duration, (int, float)):
                    duration_hours = float(duration)
                elif isinstance(duration, str):
                    # Try to extract hours (e.g., "120 hours", "5 months")
                    import re
                    hours_match = re.search(r'(\d+)\s*hours?', duration.lower())
                    if hours_match:
                        duration_hours = float(hours_match.group(1))

            difficulty_level = (
                item.get("difficulty_level") or
                item.get("difficulty") or
                item.get("level")
            )

            # Calculate fit score if provided
            fit_score = 0.0
            if "relevance_score" in item:
                fit_score = float(item["relevance_score"])
            elif "score" in item:
                fit_score = float(item["score"])
            elif "fit_score" in item:
                fit_score = float(item["fit_score"])

            # Ensure score is in [0, 1]
            fit_score = max(0.0, min(1.0, fit_score))

            return CatalogResult(
                program_key=program_key,
                program_title=program_title,
                program_type=program_type,
                summary=summary,
                duration_hours=duration_hours,
                difficulty_level=difficulty_level,
                fit_score=fit_score
            )

        except Exception as e:
            logger.warning(f"Failed to parse catalog item: {e}")
            return None

    def is_available(self) -> bool:
        """Check if the API is currently available."""
        return self._is_available

    def get_last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error

    def reset_availability(self) -> None:
        """Reset availability flag (useful for retrying after errors)."""
        self._is_available = True
        self._last_error = None
