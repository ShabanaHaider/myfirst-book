"""
Unit Tests for Orchestration Models

Tests for the orchestration request/response models and related data structures.
"""
import pytest
from datetime import datetime
from src.models.orchestration_models import (
    ChunkMetadata,
    RetrievedChunk,
    OrchestrationRequest,
    SourceAttribution,
    LLMUsageMetrics,
    OrchestrationResponse,
    OrchestrationConfig,
    QueryValidationResult,
    OrchestrationStatus,
    create_default_request,
    create_default_response
)


class TestChunkMetadata:
    """Test cases for ChunkMetadata model."""

    def test_chunk_metadata_creation(self):
        """Test creating ChunkMetadata with required fields."""
        metadata = ChunkMetadata(
            source_file_path="docs/test.md",
            chunk_index=1,
            character_position=0,
            content_hash="abc123",
            original_content_length=100
        )

        assert metadata.source_file_path == "docs/test.md"
        assert metadata.chunk_index == 1
        assert metadata.character_position == 0
        assert metadata.content_hash == "abc123"
        assert metadata.original_content_length == 100

    def test_chunk_metadata_optional_fields(self):
        """Test ChunkMetadata with optional fields."""
        metadata = ChunkMetadata(
            source_file_path="docs/test.md",
            chunk_index=1,
            character_position=0,
            content_hash="abc123",
            original_content_length=100,
            score=0.8,
            title="Test Title",
            section="Test Section"
        )

        assert metadata.score == 0.8
        assert metadata.title == "Test Title"
        assert metadata.section == "Test Section"


class TestRetrievedChunk:
    """Test cases for RetrievedChunk model."""

    def test_retrieved_chunk_creation(self):
        """Test creating RetrievedChunk with required fields."""
        metadata = ChunkMetadata(
            source_file_path="docs/test.md",
            chunk_index=1,
            character_position=0,
            content_hash="abc123",
            original_content_length=100
        )

        chunk = RetrievedChunk(
            id="chunk-1",
            content="This is the chunk content.",
            metadata=metadata
        )

        assert chunk.id == "chunk-1"
        assert chunk.content == "This is the chunk content."
        assert chunk.metadata == metadata
        assert isinstance(chunk.created_at, datetime)

    def test_retrieved_chunk_defaults(self):
        """Test RetrievedChunk with default values."""
        metadata = ChunkMetadata(
            source_file_path="docs/test.md",
            chunk_index=1,
            character_position=0,
            content_hash="abc123",
            original_content_length=100
        )

        chunk = RetrievedChunk(
            id="chunk-2",
            content="Another chunk.",
            metadata=metadata
        )

        assert chunk.id == "chunk-2"
        assert chunk.content == "Another chunk."
        assert chunk.metadata.source_file_path == "docs/test.md"


class TestOrchestrationRequest:
    """Test cases for OrchestrationRequest model."""

    def test_orchestration_request_creation(self):
        """Test creating OrchestrationRequest with required fields."""
        request = OrchestrationRequest(
            query="What is the RAG system?"
        )

        assert request.query == "What is the RAG system?"
        assert request.retrieved_chunks == []
        assert isinstance(request.timestamp, datetime)
        assert request.timeout_seconds == 30.0

    def test_orchestration_request_with_chunks(self):
        """Test OrchestrationRequest with retrieved chunks."""
        metadata = ChunkMetadata(
            source_file_path="docs/test.md",
            chunk_index=1,
            character_position=0,
            content_hash="abc123",
            original_content_length=100
        )

        chunk = RetrievedChunk(
            id="chunk-1",
            content="This is the chunk content.",
            metadata=metadata
        )

        request = OrchestrationRequest(
            query="What is the RAG system?",
            retrieved_chunks=[chunk],
            max_chunks=5
        )

        assert len(request.retrieved_chunks) == 1
        assert request.retrieved_chunks[0].id == "chunk-1"
        assert request.max_chunks == 5

    def test_orchestration_request_context_parameters(self):
        """Test OrchestrationRequest with context parameters."""
        request = OrchestrationRequest(
            query="How does it work?",
            context_parameters={
                "max_context_tokens": 2000,
                "temperature": 0.7
            }
        )

        assert request.context_parameters["max_context_tokens"] == 2000
        assert request.context_parameters["temperature"] == 0.7


class TestSourceAttribution:
    """Test cases for SourceAttribution model."""

    def test_source_attribution_creation(self):
        """Test creating SourceAttribution with required fields."""
        attribution = SourceAttribution(
            chunk_id="chunk-1",
            source_file_path="docs/test.md",
            chunk_index=1,
            snippet="This is a sample snippet."
        )

        assert attribution.chunk_id == "chunk-1"
        assert attribution.source_file_path == "docs/test.md"
        assert attribution.chunk_index == 1
        assert attribution.snippet == "This is a sample snippet."

    def test_source_attribution_optional_fields(self):
        """Test SourceAttribution with optional fields."""
        attribution = SourceAttribution(
            chunk_id="chunk-1",
            source_file_path="docs/test.md",
            chunk_index=1,
            similarity_score=0.85,
            snippet="This is a sample snippet."
        )

        assert attribution.similarity_score == 0.85


class TestLLMUsageMetrics:
    """Test cases for LLMUsageMetrics model."""

    def test_llm_usage_metrics_creation(self):
        """Test creating LLMUsageMetrics with required fields."""
        metrics = LLMUsageMetrics(
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150,
            model_name="gemini-2.5-flash",
            processing_time_ms=123.45
        )

        assert metrics.prompt_tokens == 50
        assert metrics.completion_tokens == 100
        assert metrics.total_tokens == 150
        assert metrics.model_name == "gemini-2.5-flash"
        assert metrics.processing_time_ms == 123.45


class TestOrchestrationResponse:
    """Test cases for OrchestrationResponse model."""

    def test_orchestration_response_creation(self):
        """Test creating OrchestrationResponse with required fields."""
        response = OrchestrationResponse(
            answer="This is the answer to your question."
        )

        assert response.answer == "This is the answer to your question."
        assert response.sources == []
        assert response.status == OrchestrationStatus.COMPLETED
        assert isinstance(response.timestamp, datetime)

    def test_orchestration_response_with_sources(self):
        """Test OrchestrationResponse with sources."""
        source = SourceAttribution(
            chunk_id="chunk-1",
            source_file_path="docs/test.md",
            chunk_index=1,
            snippet="This is a sample snippet."
        )

        usage = LLMUsageMetrics(
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150,
            model_name="gemini-2.5-flash",
            processing_time_ms=123.45
        )

        response = OrchestrationResponse(
            answer="This is the answer.",
            sources=[source],
            usage_metrics=usage,
            confidence=0.85
        )

        assert len(response.sources) == 1
        assert response.sources[0].chunk_id == "chunk-1"
        assert response.usage_metrics == usage
        assert response.confidence == 0.85

    def test_orchestration_response_status(self):
        """Test OrchestrationResponse with different statuses."""
        response = OrchestrationResponse(
            answer="This is the answer.",
            status=OrchestrationStatus.FAILED,
            error_message="An error occurred."
        )

        assert response.status == OrchestrationStatus.FAILED
        assert response.error_message == "An error occurred."


class TestOrchestrationConfig:
    """Test cases for OrchestrationConfig model."""

    def test_orchestration_config_creation(self):
        """Test creating OrchestrationConfig with default values."""
        config = OrchestrationConfig()

        assert config.max_context_tokens == 3000
        assert config.max_response_tokens == 1024
        assert config.min_chunk_score == 0.3
        assert config.max_chunks_to_process == 10
        assert config.enable_source_citations is True

    def test_orchestration_config_custom_values(self):
        """Test OrchestrationConfig with custom values."""
        config = OrchestrationConfig(
            max_context_tokens=2000,
            max_response_tokens=512,
            min_chunk_score=0.5,
            enable_cache=False
        )

        assert config.max_context_tokens == 2000
        assert config.max_response_tokens == 512
        assert config.min_chunk_score == 0.5
        assert config.enable_cache is False


class TestQueryValidationResult:
    """Test cases for QueryValidationResult model."""

    def test_query_validation_result_creation(self):
        """Test creating QueryValidationResult."""
        result = QueryValidationResult(
            is_valid=True,
            errors=[],
            warnings=["This is a warning"]
        )

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == ["This is a warning"]

    def test_query_validation_result_invalid(self):
        """Test QueryValidationResult for invalid query."""
        result = QueryValidationResult(
            is_valid=False,
            errors=["Query is too short"],
            warnings=[]
        )

        assert result.is_valid is False
        assert result.errors == ["Query is too short"]
        assert result.warnings == []


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_create_default_request(self):
        """Test creating a default orchestration request."""
        request = create_default_request("Test query")

        assert request.query == "Test query"
        assert request.retrieved_chunks == []
        assert "max_context_tokens" in request.context_parameters

    def test_create_default_request_with_chunks(self):
        """Test creating a default request with chunks."""
        metadata = ChunkMetadata(
            source_file_path="docs/test.md",
            chunk_index=1,
            character_position=0,
            content_hash="abc123",
            original_content_length=100
        )

        chunk = RetrievedChunk(
            id="chunk-1",
            content="This is the chunk content.",
            metadata=metadata
        )

        request = create_default_request("Test query", retrieved_chunks=[chunk])

        assert request.query == "Test query"
        assert len(request.retrieved_chunks) == 1
        assert request.retrieved_chunks[0].id == "chunk-1"

    def test_create_default_response(self):
        """Test creating a default orchestration response."""
        response = create_default_response("Test answer")

        assert response.answer == "Test answer"
        assert response.sources == []
        assert response.status == OrchestrationStatus.COMPLETED

    def test_create_default_response_with_sources(self):
        """Test creating a default response with sources."""
        source = SourceAttribution(
            chunk_id="chunk-1",
            source_file_path="docs/test.md",
            chunk_index=1,
            snippet="This is a sample snippet."
        )

        response = create_default_response("Test answer", sources=[source])

        assert response.answer == "Test answer"
        assert len(response.sources) == 1
        assert response.sources[0].chunk_id == "chunk-1"


class TestEdgeCases:
    """Test edge cases for orchestration models."""

    def test_empty_strings(self):
        """Test models with empty strings."""
        request = OrchestrationRequest(query="")
        assert request.query == ""

        response = OrchestrationResponse(answer="")
        assert response.answer == ""

    def test_none_values_handling(self):
        """Test models with None values where allowed."""
        source = SourceAttribution(
            chunk_id="chunk-1",
            source_file_path="docs/test.md",
            chunk_index=1,
            similarity_score=None,  # This should be allowed
            snippet=""
        )

        assert source.similarity_score is None

    def test_large_content(self):
        """Test models with large content."""
        large_content = "A" * 10000  # 10k characters

        request = OrchestrationRequest(query=large_content)
        assert request.query == large_content

        response = OrchestrationResponse(answer=large_content)
        assert response.answer == large_content

    def test_datetime_serialization(self):
        """Test that datetime fields work correctly."""
        now = datetime.now()
        request = OrchestrationRequest(query="Test", timestamp=now)
        assert request.timestamp == now

        response = OrchestrationResponse(answer="Test", timestamp=now)
        assert response.timestamp == now


if __name__ == "__main__":
    pytest.main([__file__])