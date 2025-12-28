"""
Unit tests for query functionality.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.query.query_processor import QueryProcessor
from src.query.response_generator import ResponseGenerator
from src.services.retrieval_service import RetrievalService
from src.query.query_validator import QueryValidator
from src.config.settings import settings


@pytest.fixture
def query_processor():
    """Fixture to create a QueryProcessor instance."""
    with patch('src.clients.cohere_client.CohereWrapper') as mock_cohere:
        processor = QueryProcessor()
        processor.cohere_client = mock_cohere
        yield processor


@pytest.fixture
def response_generator():
    """Fixture to create a ResponseGenerator instance."""
    generator = ResponseGenerator()
    yield generator


@pytest.fixture
def query_validator():
    """Fixture to create a QueryValidator instance."""
    validator = QueryValidator()
    yield validator


class TestQueryProcessor:
    """Unit tests for QueryProcessor."""

    @pytest.mark.asyncio
    async def test_process_query_success(self, query_processor):
        """Test successful query processing."""
        # Mock the Cohere client to return a sample embedding
        query_processor.cohere_client.embed_query = AsyncMock(return_value=[0.1] * 1024)
        query_processor.cohere_client.validate_embeddings = MagicMock(return_value=True)

        query = "What is the main concept?"
        result = await query_processor.process_query(query)

        assert result["original_query"] == query
        assert result["processed_query"] == "What is the main concept?"
        assert result["embedding"] == [0.1] * 1024
        assert isinstance(result["query_length"], int)

    @pytest.mark.asyncio
    async def test_process_query_empty(self, query_processor):
        """Test query processing with empty query."""
        with pytest.raises(Exception):  # Could be ValidationError
            await query_processor.process_query("")

    @pytest.mark.asyncio
    async def test_process_query_too_long(self, query_processor):
        """Test query processing with overly long query."""
        long_query = "This is a very long query. " * 100  # This should exceed our limit
        with pytest.raises(Exception):  # Could be ValidationError
            await query_processor.process_query(long_query)

    @pytest.mark.asyncio
    async def test_preprocess_query(self, query_processor):
        """Test query preprocessing."""
        raw_query = "  This   has   extra   spaces  "
        processed = query_processor.preprocess_query(raw_query)
        assert processed == "This has extra spaces"

    @pytest.mark.asyncio
    async def test_batch_process_queries(self, query_processor):
        """Test batch processing of queries."""
        # Mock the Cohere client
        query_processor.cohere_client.embed_query = AsyncMock(return_value=[0.1] * 1024)
        query_processor.cohere_client.validate_embeddings = MagicMock(return_value=True)

        queries = ["Query 1", "Query 2"]
        results = await query_processor.batch_process_queries(queries)

        assert len(results) == 2
        for result in results:
            assert "original_query" in result
            assert "processed_query" in result or "error" in result

    @pytest.mark.asyncio
    async def test_validate_query_quality(self, query_processor):
        """Test query quality validation."""
        validation_result = await query_processor.validate_query_quality("Good query")
        assert isinstance(validation_result, dict)
        assert "is_valid" in validation_result
        assert "issues" in validation_result

    @pytest.mark.asyncio
    async def test_validate_query_quality_short(self, query_processor):
        """Test query quality validation for short queries."""
        validation_result = await query_processor.validate_query_quality("hi")
        assert validation_result["is_valid"] is False
        assert len(validation_result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_expand_query(self, query_processor):
        """Test query expansion."""
        query = "machine learning"
        expanded = await query_processor.expand_query(query)
        assert isinstance(expanded, list)
        assert query in expanded
        assert "machine" in expanded or "learning" in expanded

    @pytest.mark.asyncio
    async def test_extract_query_entities(self, query_processor):
        """Test entity extraction from query."""
        query = "Tell me about machine learning algorithms"
        entities = await query_processor.extract_query_entities(query)
        assert isinstance(entities, list)
        # Should not include stop words
        assert "me" not in entities
        assert "about" not in entities
        # Should include meaningful terms
        assert "machine" in entities or "learning" in entities or "algorithms" in entities


class TestResponseGenerator:
    """Unit tests for ResponseGenerator."""

    def test_generate_response_no_results(self, response_generator):
        """Test response generation with no search results."""
        result = response_generator.generate_response("test query", [])
        assert "I couldn't find any relevant information" in result["response"]
        assert result["confidence"] == 0.0
        assert len(result["sources"]) == 0

    def test_generate_response_with_results(self, response_generator):
        """Test response generation with search results."""
        search_results = [
            {
                "payload": {
                    "text_content": "This is relevant content",
                    "source_file_path": "test.md",
                    "chunk_index": 1
                },
                "score": 0.8
            }
        ]
        result = response_generator.generate_response("test query", search_results)
        assert result["response"]
        assert len(result["sources"]) == 1
        assert result["sources"][0]["source_file"] == "test.md"

    def test_generate_condensed_response(self, response_generator):
        """Test condensed response generation."""
        search_results = [
            {
                "payload": {
                    "text_content": "This is relevant content. " * 500,  # Long content
                    "source_file_path": "test.md",
                    "chunk_index": 1
                },
                "score": 0.8
            }
        ]
        result = response_generator.generate_condensed_response("test query", search_results, max_response_length=100)
        assert len(result["response"]) <= 103  # 100 + 3 for "..."

    def test_format_sources(self, response_generator):
        """Test source formatting."""
        sources = [
            {
                "source_file": "doc1.md",
                "chunk_index": 1,
                "similarity_score": 0.9
            },
            {
                "source_file": "doc2.md",
                "chunk_index": 2,
                "similarity_score": 0.8
            }
        ]
        formatted = response_generator.format_sources(sources)
        assert "doc1.md" in formatted
        assert "doc2.md" in formatted
        assert "Score: 0.90" in formatted

    def test_calculate_response_confidence(self, response_generator):
        """Test confidence calculation."""
        search_results = [
            {"score": 0.9},
            {"score": 0.7},
            {"score": 0.5}
        ]
        confidence = response_generator.calculate_response_confidence(search_results)
        assert 0.0 <= confidence <= 1.0

    def test_generate_fallback_response(self, response_generator):
        """Test fallback response generation."""
        result = response_generator.generate_fallback_response("test query")
        assert "couldn't find specific information" in result["response"]
        assert result["confidence"] == 0.0
        assert len(result["sources"]) == 0

    def test_validate_response_quality(self, response_generator):
        """Test response quality validation."""
        response = {
            "response": "This is a good response",
            "sources": [{"source_file": "test.md"}],
            "confidence": 0.8
        }
        validation = response_generator.validate_response_quality(response, "test query")
        assert isinstance(validation, dict)
        assert "is_valid" in validation
        assert "quality_score" in validation


class TestQueryValidator:
    """Unit tests for QueryValidator."""

    def test_validate_query_text_valid(self, query_validator):
        """Test validation of a valid query."""
        result = QueryValidator.validate_query_text("This is a valid query")
        assert result["is_valid"] is True
        assert len(result["issues"]) == 0

    def test_validate_query_text_empty(self, query_validator):
        """Test validation of an empty query."""
        result = QueryValidator.validate_query_text("")
        assert result["is_valid"] is False
        assert len(result["issues"]) > 0

    def test_validate_query_text_too_long(self, query_validator):
        """Test validation of an overly long query."""
        long_query = "x" * (settings.MAX_QUERY_LENGTH + 1)
        result = QueryValidator.validate_query_text(long_query)
        assert result["is_valid"] is False
        assert len(result["issues"]) > 0

    def test_validate_top_k_valid(self, query_validator):
        """Test validation of valid top_k value."""
        result = QueryValidator.validate_top_k(5)
        assert result["is_valid"] is True
        assert result["value"] == 5

    def test_validate_top_k_invalid(self, query_validator):
        """Test validation of invalid top_k value."""
        result = QueryValidator.validate_top_k(25)  # Too high
        assert result["is_valid"] is False
        assert len(result["issues"]) > 0

    def test_validate_similarity_threshold_valid(self, query_validator):
        """Test validation of valid similarity threshold."""
        result = QueryValidator.validate_similarity_threshold(0.7)
        assert result["is_valid"] is True
        assert result["value"] == 0.7

    def test_validate_similarity_threshold_invalid(self, query_validator):
        """Test validation of invalid similarity threshold."""
        result = QueryValidator.validate_similarity_threshold(1.5)  # Too high
        assert result["is_valid"] is False
        assert len(result["issues"]) > 0

    def test_validate_full_query_request_valid(self, query_validator):
        """Test validation of a full query request."""
        result = QueryValidator.validate_full_query_request("valid query", 5, 0.7)
        assert result["is_valid"] is True

    def test_validate_full_query_request_invalid(self, query_validator):
        """Test validation of an invalid query request."""
        result = QueryValidator.validate_full_query_request("", 25, 1.5)  # All invalid
        assert result["is_valid"] is False

    def test_suggest_query_improvements(self, query_validator):
        """Test query improvement suggestions."""
        result = QueryValidator.suggest_query_improvements("short")
        assert isinstance(result, dict)
        assert "original_query" in result
        assert "improvements" in result

    def test_validate_and_enhance_query(self, query_validator):
        """Test comprehensive query validation and enhancement."""
        result = QueryValidator.validate_and_enhance_query("valid query")
        assert isinstance(result, dict)
        assert "validation" in result
        assert "improvements" in result
        assert "is_processable" in result