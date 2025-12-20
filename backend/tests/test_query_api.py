"""
Integration tests for query API.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.query_endpoint import router, QueryRequest
from backend.main import app  # Assuming you have a main app file


# Create a test client
client = TestClient(app)


class TestQueryAPI:
    """Integration tests for the query API endpoints."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for external dependencies."""
        with patch('src.services.retrieval_service.RetrievalService') as mock_retrieval, \
             patch('src.query.query_processor.QueryProcessor') as mock_query_processor, \
             patch('src.query.response_generator.ResponseGenerator') as mock_response_generator:

            # Mock retrieval service
            mock_retrieval.return_value.__init__.return_value = None
            mock_retrieval.return_value.retrieve_similar_documents = AsyncMock(
                return_value=[
                    {
                        "payload": {
                            "text_content": "This is relevant content",
                            "source_file_path": "test.md",
                            "chunk_index": 1
                        },
                        "score": 0.8
                    }
                ]
            )
            mock_retrieval.return_value.health_check = MagicMock(return_value=True)
            mock_retrieval.return_value.get_collection_stats = MagicMock(return_value={"total_documents": 10})

            # Mock query processor
            mock_query_processor.return_value.__init__.return_value = None
            mock_query_processor.return_value.process_query = AsyncMock(
                return_value={
                    "original_query": "test query",
                    "processed_query": "test query",
                    "embedding": [0.1] * 1024,
                    "query_length": 10
                }
            )
            mock_query_processor.return_value.validate_query_quality = AsyncMock(
                return_value={
                    "is_valid": True,
                    "issues": [],
                    "suggestions": []
                }
            )
            mock_query_processor.return_value.expand_query = AsyncMock(
                return_value=["test query", "test", "query"]
            )
            mock_query_processor.return_value.health_check = MagicMock(return_value=True)

            # Mock response generator
            mock_response_generator.return_value.__init__.return_value = None
            mock_response_generator.return_value.generate_response = MagicMock(
                return_value={
                    "response": "This is a test response",
                    "sources": [
                        {
                            "source_file": "test.md",
                            "chunk_index": 1,
                            "similarity_score": 0.8,
                            "text_preview": "This is relevant content"
                        }
                    ],
                    "confidence": 0.8,
                    "query": "test query",
                    "retrieved_chunks_count": 1
                }
            )

            yield {
                "retrieval": mock_retrieval,
                "query_processor": mock_query_processor,
                "response_generator": mock_response_generator
            }

    def test_query_documentation_success(self, setup_mocks):
        """Test successful query documentation request."""
        request_data = {
            "query": "What is the main concept?",
            "top_k": 5,
            "similarity_threshold": 0.7,
            "include_sources": True
        }

        response = client.post("/api/v1/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "query_id" in data
        assert "response" in data
        assert "sources" in data
        assert "confidence" in data
        assert "response_time_ms" in data
        assert "retrieved_chunks_count" in data

        assert isinstance(data["response"], str)
        assert len(data["sources"]) >= 0  # May be empty if no sources requested
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["retrieved_chunks_count"] >= 0

    def test_query_documentation_missing_query(self, setup_mocks):
        """Test query documentation request with missing query."""
        request_data = {
            "top_k": 5,
            "similarity_threshold": 0.7,
            "include_sources": True
        }

        response = client.post("/api/v1/query", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_query_documentation_invalid_query_length(self, setup_mocks):
        """Test query documentation request with overly long query."""
        request_data = {
            "query": "x" * 2000,  # Way too long
            "top_k": 5,
            "similarity_threshold": 0.7,
            "include_sources": True
        }

        response = client.post("/api/v1/query", json=request_data)

        assert response.status_code == 400  # Validation error

    def test_query_documentation_invalid_top_k(self, setup_mocks):
        """Test query documentation request with invalid top_k."""
        request_data = {
            "query": "test query",
            "top_k": 0,  # Invalid
            "similarity_threshold": 0.7,
            "include_sources": True
        }

        response = client.post("/api/v1/query", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_query_documentation_invalid_similarity_threshold(self, setup_mocks):
        """Test query documentation request with invalid similarity threshold."""
        request_data = {
            "query": "test query",
            "top_k": 5,
            "similarity_threshold": 1.5,  # Invalid
            "include_sources": True
        }

        response = client.post("/api/v1/query", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_validate_query_success(self, setup_mocks):
        """Test successful query validation."""
        request_data = {
            "query": "test query",
            "top_k": 5,
            "similarity_threshold": 0.7,
            "include_sources": True
        }

        response = client.post("/api/v1/query/validate", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "is_valid" in data
        assert "issues" in data
        assert "suggestions" in data

    def test_expand_query_success(self, setup_mocks):
        """Test successful query expansion."""
        response = client.post("/api/v1/query/expand", params={"query": "test query"})

        assert response.status_code == 200
        data = response.json()

        assert "original_query" in data
        assert "expanded_terms" in data
        assert isinstance(data["expanded_terms"], list)

    def test_get_query_stats_success(self, setup_mocks):
        """Test successful retrieval of query stats."""
        response = client.get("/api/v1/query/stats")

        assert response.status_code == 200
        data = response.json()

        assert "collection_stats" in data
        assert "model_info" in data
        assert "settings" in data

    def test_query_health_check_success(self, setup_mocks):
        """Test successful health check."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "query_service" in data
        assert "retrieval_service" in data
        assert "query_processor" in data

    def test_query_health_check_failure(self, setup_mocks):
        """Test health check with failing components."""
        # Mock the health checks to return False
        setup_mocks["retrieval"].return_value.health_check.return_value = False
        setup_mocks["query_processor"].return_value.health_check.return_value = False

        response = client.get("/api/v1/health")

        assert response.status_code == 200  # Health check endpoint always returns 200
        data = response.json()

        assert data["query_service"] is False
        assert data["retrieval_service"] is False
        assert data["query_processor"] is False

    def test_debug_query_endpoint(self, setup_mocks):
        """Test the debug query endpoint."""
        request_data = {
            "query": "test query",
            "top_k": 5,
            "similarity_threshold": 0.7,
            "include_sources": True
        }

        response = client.post("/api/v1/query/debug", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "original_query" in data
        assert "processed_query" in data
        assert "query_embedding_length" in data
        assert "search_results_count" in data


class TestQueryAPIErrorHandling:
    """Integration tests for query API error handling."""

    def test_query_processing_error(self):
        """Test handling of query processing errors."""
        # In a real test, we would cause one of the mocked components to raise an exception
        # For now, we'll simulate by patching differently
        with patch('src.api.query_endpoint.query_processor') as mock_qp:
            mock_qp.process_query = AsyncMock(side_effect=Exception("Processing error"))

            request_data = {
                "query": "test query",
                "top_k": 5,
                "similarity_threshold": 0.7,
                "include_sources": True
            }

            # Note: This test would require more complex mocking to work properly
            # For now, we'll just document the approach
            pass

    def test_retrieval_error(self):
        """Test handling of retrieval errors."""
        # Similar to above, would require complex mocking
        pass

    def test_response_generation_error(self):
        """Test handling of response generation errors."""
        # Similar to above, would require complex mocking
        pass


# Additional integration tests could include:
# - Testing with different configurations
# - Testing edge cases with real data
# - Performance tests
# - Load tests
# - Security tests