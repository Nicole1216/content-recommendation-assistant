"""Tests for CatalogAPIProvider (Phase 3.5)."""

import pytest
from unittest.mock import Mock, patch
import requests
from retrieval.catalog_api_provider import CatalogAPIProvider
from schemas.evidence import CatalogResult


class TestCatalogAPIProvider:
    """Test Catalog API provider with real API integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = "https://api.udacity.com/api/unified-catalog"
        self.provider = CatalogAPIProvider(base_url=self.base_url, timeout=5)

    def test_initialization(self):
        """Test provider initialization."""
        assert self.provider.base_url == self.base_url
        assert self.provider.timeout == 5
        assert self.provider.is_available() is True

    def test_initialization_with_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        provider = CatalogAPIProvider(base_url="https://api.udacity.com/api/unified-catalog/")
        assert provider.base_url == self.base_url

    @patch('requests.get')
    def test_search_success(self, mock_get):
        """Test successful search."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "program_key": "cd0101",
                    "program_title": "Generative AI for Business Leaders",
                    "program_type": "Course",
                    "summary": "Non-technical introduction to GenAI",
                    "duration_hours": 8.0,
                    "difficulty_level": "Beginner",
                    "relevance_score": 0.95
                },
                {
                    "key": "cd0102",
                    "title": "Data Analyst Nanodegree",
                    "type": "Nanodegree",
                    "description": "Master SQL, Python, and data visualization",
                    "duration": 180,
                    "level": "Intermediate",
                    "score": 0.85
                }
            ]
        }
        mock_get.return_value = mock_response

        # Test search
        results = self.provider.search("GenAI", top_k=5)

        # Verify
        assert len(results) == 2
        assert isinstance(results[0], CatalogResult)
        assert results[0].program_key == "cd0101"
        assert results[0].program_title == "Generative AI for Business Leaders"
        assert results[0].fit_score == 0.95
        assert results[1].program_key == "cd0102"
        assert results[1].fit_score == 0.85

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == f"{self.base_url}/search"
        assert call_args[1]["params"]["q"] == "GenAI"
        assert call_args[1]["params"]["limit"] == 5

    @patch('requests.get')
    def test_search_with_filters(self, mock_get):
        """Test search with filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        # Test with filters
        filters = {"program_type": "Nanodegree", "difficulty_level": "Advanced"}
        results = self.provider.search("Python", top_k=3, filters=filters)

        # Verify filters were passed
        call_args = mock_get.call_args
        assert call_args[1]["params"]["program_type"] == "Nanodegree"
        assert call_args[1]["params"]["difficulty_level"] == "Advanced"

    @patch('requests.get')
    def test_search_timeout(self, mock_get):
        """Test search with timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()

        results = self.provider.search("Python")

        assert results == []
        assert self.provider.is_available() is False
        assert "timeout" in self.provider.get_last_error().lower()

    @patch('requests.get')
    def test_search_401_unauthorized(self, mock_get):
        """Test search with 401 authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        results = self.provider.search("Python")

        assert results == []
        assert self.provider.is_available() is False
        assert "authentication" in self.provider.get_last_error().lower()

    @patch('requests.get')
    def test_search_403_forbidden(self, mock_get):
        """Test search with 403 forbidden error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        results = self.provider.search("Python")

        assert results == []
        assert self.provider.is_available() is False

    @patch('requests.get')
    def test_search_connection_error(self, mock_get):
        """Test search with connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        results = self.provider.search("Python")

        assert results == []
        assert self.provider.is_available() is False

    @patch('requests.get')
    def test_search_empty_response(self, mock_get):
        """Test search with empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        results = self.provider.search("XYZ123")

        assert results == []
        assert self.provider.is_available() is True  # API is available, just no results

    @patch('requests.get')
    def test_search_alternative_response_format(self, mock_get):
        """Test search with alternative response format (direct array)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "program_key": "cd0101",
                "program_title": "GenAI Course",
                "program_type": "Course",
                "summary": "Test course"
            }
        ]
        mock_get.return_value = mock_response

        results = self.provider.search("GenAI")

        assert len(results) == 1
        assert results[0].program_key == "cd0101"

    @patch('requests.get')
    def test_get_by_key_success(self, mock_get):
        """Test successful get by key."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "program": {
                "program_key": "cd0101",
                "program_title": "GenAI for Business",
                "program_type": "Course",
                "summary": "Test course",
                "duration_hours": 8.0,
                "difficulty_level": "Beginner"
            }
        }
        mock_get.return_value = mock_response

        result = self.provider.get_by_key("cd0101")

        assert result is not None
        assert result.program_key == "cd0101"
        assert result.program_title == "GenAI for Business"

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == f"{self.base_url}/programs/cd0101"

    @patch('requests.get')
    def test_get_by_key_404_not_found(self, mock_get):
        """Test get by key with 404 not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.provider.get_by_key("nonexistent")

        assert result is None
        # API is still available, just program not found
        assert self.provider.is_available() is True

    @patch('requests.get')
    def test_get_by_key_timeout(self, mock_get):
        """Test get by key with timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()

        result = self.provider.get_by_key("cd0101")

        assert result is None
        assert self.provider.is_available() is False

    @patch('requests.get')
    def test_parse_catalog_item_various_field_names(self, mock_get):
        """Test parsing items with various field naming conventions."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "cd0101",
                    "name": "Course Name",
                    "type": "Course",
                    "overview": "Course overview"
                },
                {
                    "key": "cd0102",
                    "title": "Another Course",
                    "product_type": "Nanodegree",
                    "description": "Course description",
                    "duration": "120 hours"
                }
            ]
        }
        mock_get.return_value = mock_response

        results = self.provider.search("test")

        assert len(results) == 2
        assert results[0].program_key == "cd0101"
        assert results[0].program_title == "Course Name"
        assert results[0].summary == "Course overview"
        assert results[1].program_key == "cd0102"
        assert results[1].duration_hours == 120.0

    @patch('requests.get')
    def test_fit_score_normalization(self, mock_get):
        """Test that fit scores are normalized to [0, 1]."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"program_key": "cd0101", "program_title": "Test", "program_type": "Course",
                 "summary": "Test", "score": 1.5},  # > 1
                {"program_key": "cd0102", "program_title": "Test", "program_type": "Course",
                 "summary": "Test", "score": -0.5}  # < 0
            ]
        }
        mock_get.return_value = mock_response

        results = self.provider.search("test")

        # Scores should be clamped to [0, 1]
        assert results[0].fit_score == 1.0
        assert results[1].fit_score == 0.0

    def test_reset_availability(self):
        """Test resetting availability after error."""
        # Simulate error
        self.provider._is_available = False
        self.provider._last_error = "Test error"

        assert self.provider.is_available() is False

        # Reset
        self.provider.reset_availability()

        assert self.provider.is_available() is True
        assert self.provider.get_last_error() is None

    @patch('requests.get')
    def test_headers_with_auth_token(self, mock_get):
        """Test that auth token is included in headers."""
        provider = CatalogAPIProvider(
            base_url=self.base_url,
            auth_token="test_token_123"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        provider.search("test")

        # Verify auth header was included
        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token_123"

    @patch('requests.get')
    def test_unavailable_provider_returns_empty(self, mock_get):
        """Test that unavailable provider returns empty results without making calls."""
        # Make provider unavailable
        self.provider._is_available = False
        self.provider._last_error = "Previous error"

        results = self.provider.search("test")

        assert results == []
        # Should not make API call
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_search_500_error(self, mock_get):
        """Test search with 500 server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        results = self.provider.search("Python")

        assert results == []
        assert self.provider.is_available() is False
        assert "500" in self.provider.get_last_error()
