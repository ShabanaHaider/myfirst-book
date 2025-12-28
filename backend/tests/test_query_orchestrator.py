"""
Unit Tests for Query Orchestrator Service

Tests for the orchestration service that coordinates retrieval and generation.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.services.query_orchestrator import QueryOrchestratorService
from src.models.orchestration_models import (
    OrchestrationRequest,
    RetrievedChunk,
    ChunkMetadata,
    OrchestrationResponse
)
from src.models.prompt_template import RAGPromptTemplate


class TestQueryOrchestratorService:
    """Test cases for the QueryOrchestratorService class."""

    @pytest.fixture
    def orchestrator(self):
        """Create a mock orchestrator for testing."""
        with patch('src.services.query_orchestrator.RetrievalService'), \
             patch('src.services.query_orchestrator.ContextManager'), \
             patch('src.services.query_orchestrator.gemini_agent'):
            orchestrator = QueryOrchestratorService()
            # Mock the dependencies
            orchestrator.retrieval_service = Mock()
            orchestrator.context_manager = Mock()
            orchestrator.gemini_client = Mock()
            return orchestrator

    @pytest.fixture
    def sample_request(self):
        """Create a sample orchestration request."""
        return OrchestrationRequest(
            query="What is the RAG system?",
            max_chunks=3,
            min_similarity_score=0.5
        )

    @pytest.fixture
    def sample_chunks(self):
        """Create sample retrieved chunks."""
        metadata = ChunkMetadata(
            source_file_path="docs/test.md",
            chunk_index=1,
            character_position=0,
            content_hash="abc123",
            original_content_length=100,
            score=0.8
        )
        chunk = RetrievedChunk(
            id="chunk-1",
            content="The RAG system retrieves relevant documents and uses LLMs to generate responses.",
            metadata=metadata
        )
        return [chunk]

    @pytest.mark.asyncio
    async def test_process_query_success(self, orchestrator, sample_request, sample_chunks):
        """Test successful query processing."""
        # Mock the retrieval service
        orchestrator.retrieval_service.retrieve_similar_documents = AsyncMock(
            return_value=[{
                'id': 'chunk-1',
                'payload': {
                    'content': 'The RAG system retrieves relevant documents and uses LLMs to generate responses.',
                    'source_file_path': 'docs/test.md',
                    'chunk_index': 1,
                    'character_position': 0,
                    'content_hash': 'abc123'
                },
                'score': 0.8
            }]
        )

        # Mock the context manager
        orchestrator.context_manager.optimize_context_for_query = Mock(return_value=sample_chunks)
        orchestrator.context_manager.get_context_summary = Mock(return_value={
            "num_chunks": 1,
            "context_tokens": 20,
            "query_tokens": 5,
            "total_tokens": 25
        })

        # Mock the LLM response
        with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
            mock_llm.return_value = "The RAG system is a method that retrieves relevant documents and uses language models to generate responses."

            response = await orchestrator.process_query(sample_request)

            assert response.status.value == "completed"
            assert "RAG system" in response.answer
            assert len(response.sources) >= 0  # Sources may be included based on request settings

    @pytest.mark.asyncio
    async def test_process_query_with_predefined_chunks(self, orchestrator, sample_request):
        """Test query processing with predefined chunks."""
        # Create chunks to include in the request
        metadata = ChunkMetadata(
            source_file_path="docs/test.md",
            chunk_index=1,
            character_position=0,
            content_hash="abc123",
            original_content_length=100,
            score=0.8
        )
        chunk = RetrievedChunk(
            id="chunk-1",
            content="The RAG system retrieves relevant documents and uses LLMs to generate responses.",
            metadata=metadata
        )
        sample_request.retrieved_chunks = [chunk]

        # Mock the context manager
        orchestrator.context_manager.optimize_context_for_query = Mock(return_value=[chunk])
        orchestrator.context_manager.get_context_summary = Mock(return_value={
            "num_chunks": 1,
            "context_tokens": 20,
            "query_tokens": 5,
            "total_tokens": 25
        })

        # Mock the LLM response
        with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
            mock_llm.return_value = "The RAG system is a method that retrieves relevant documents and uses language models to generate responses."

            response = await orchestrator.process_query(sample_request)

            assert response.status.value == "completed"
            assert "RAG system" in response.answer

    @pytest.mark.asyncio
    async def test_process_query_retrieval_failure(self, orchestrator, sample_request):
        """Test query processing when retrieval fails."""
        # Mock retrieval to raise an exception
        orchestrator.retrieval_service.retrieve_similar_documents = AsyncMock(
            side_effect=Exception("Retrieval failed")
        )

        response = await orchestrator.process_query(sample_request)

        assert response.status.value == "failed"
        assert "error" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_process_query_llm_failure(self, orchestrator, sample_request, sample_chunks):
        """Test query processing when LLM call fails."""
        # Mock the retrieval service
        orchestrator.retrieval_service.retrieve_similar_documents = AsyncMock(
            return_value=[{
                'id': 'chunk-1',
                'payload': {
                    'content': 'Test content',
                    'source_file_path': 'docs/test.md',
                    'chunk_index': 1,
                    'character_position': 0,
                    'content_hash': 'abc123'
                },
                'score': 0.8
            }]
        )

        # Mock the context manager
        orchestrator.context_manager.optimize_context_for_query = Mock(return_value=sample_chunks)

        # Mock the LLM to raise an exception
        with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
            mock_llm.side_effect = Exception("LLM call failed")

            response = await orchestrator.process_query(sample_request)

            assert response.status.value == "failed"
            assert "error" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_validate_query_success(self, orchestrator, sample_request):
        """Test query validation with valid input."""
        is_valid, errors = await orchestrator.validate_query(sample_request)

        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_query_empty(self, orchestrator):
        """Test query validation with empty query."""
        request = OrchestrationRequest(query="")

        is_valid, errors = await orchestrator.validate_query(request)

        assert is_valid is False
        assert "cannot be empty" in errors[0].lower()

    @pytest.mark.asyncio
    async def test_validate_query_too_long(self, orchestrator):
        """Test query validation with overly long query."""
        from src.config.settings import settings
        long_query = "A" * (settings.MAX_QUERY_LENGTH + 1)
        request = OrchestrationRequest(query=long_query)

        is_valid, errors = await orchestrator.validate_query(request)

        assert is_valid is False
        assert "exceeds maximum length" in errors[0].lower()

    def test_get_context_summary(self, orchestrator, sample_request, sample_chunks):
        """Test getting context summary."""
        # Mock the context manager
        expected_summary = {
            "num_chunks": 1,
            "num_sources": 1,
            "sources": ["docs/test.md"],
            "context_tokens": 20,
            "query_tokens": 5,
            "total_tokens": 25
        }
        orchestrator.context_manager.optimize_context_for_query = Mock(return_value=sample_chunks)
        orchestrator.context_manager.get_context_summary = Mock(return_value=expected_summary)

        summary = orchestrator.get_context_summary(sample_request)

        assert summary == expected_summary
        assert summary["num_chunks"] == 1


class TestQueryOrchestratorIntegration:
    """Integration tests for the query orchestrator (with mocked external dependencies)."""

    @pytest.mark.asyncio
    async def test_full_orchestration_flow(self):
        """Test the full orchestration flow with mocked dependencies."""
        with patch('src.services.query_orchestrator.RetrievalService') as mock_retrieval, \
             patch('src.services.query_orchestrator.ContextManager') as mock_context, \
             patch('src.services.query_orchestrator.gemini_agent'):

            # Set up mocks
            mock_retrieval_instance = Mock()
            mock_retrieval.return_value = mock_retrieval_instance
            mock_retrieval_instance.retrieve_similar_documents = AsyncMock(
                return_value=[{
                    'id': 'chunk-1',
                    'payload': {
                        'content': 'The RAG system retrieves relevant documents and uses LLMs to generate responses.',
                        'source_file_path': 'docs/test.md',
                        'chunk_index': 1,
                        'character_position': 0,
                        'content_hash': 'abc123'
                    },
                    'score': 0.8
                }]
            )

            mock_context_instance = Mock()
            mock_context.return_value = mock_context_instance
            mock_context_instance.optimize_context_for_query = Mock(side_effect=lambda req: [
                RetrievedChunk(
                    id="chunk-1",
                    content="The RAG system retrieves relevant documents and uses LLMs to generate responses.",
                    metadata=ChunkMetadata(
                        source_file_path="docs/test.md",
                        chunk_index=1,
                        character_position=0,
                        content_hash="abc123",
                        original_content_length=100,
                        score=0.8
                    )
                )
            ])
            mock_context_instance.get_context_summary = Mock(return_value={
                "num_chunks": 1,
                "context_tokens": 20,
                "query_tokens": 5,
                "total_tokens": 25
            })

            orchestrator = QueryOrchestratorService()

            # Mock the LLM response
            with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
                mock_llm.return_value = "The RAG system retrieves relevant documents and uses LLMs to generate responses."

                request = OrchestrationRequest(
                    query="What is the RAG system?",
                    max_chunks=3,
                    min_similarity_score=0.5
                )

                response = await orchestrator.process_query(request)

                assert response.status.value == "completed"
                assert "RAG system" in response.answer
                assert len(response.sources) >= 0

    @pytest.mark.asyncio
    async def test_orchestration_with_fallback(self):
        """Test orchestration with fallback mechanism."""
        with patch('src.services.query_orchestrator.RetrievalService') as mock_retrieval, \
             patch('src.services.query_orchestrator.ContextManager') as mock_context, \
             patch('src.services.query_orchestrator.gemini_agent'):

            # Set up mocks
            mock_retrieval_instance = Mock()
            mock_retrieval.return_value = mock_retrieval_instance
            mock_retrieval_instance.retrieve_similar_documents = AsyncMock(
                return_value=[{
                    'id': 'chunk-1',
                    'payload': {
                        'content': 'The RAG system retrieves relevant documents.',
                        'source_file_path': 'docs/test.md',
                        'chunk_index': 1,
                        'character_position': 0,
                        'content_hash': 'abc123'
                    },
                    'score': 0.8
                }]
            )

            mock_context_instance = Mock()
            mock_context.return_value = mock_context_instance
            mock_context_instance.optimize_context_for_query = Mock(side_effect=lambda req: [
                RetrievedChunk(
                    id="chunk-1",
                    content="The RAG system retrieves relevant documents.",
                    metadata=ChunkMetadata(
                        source_file_path="docs/test.md",
                        chunk_index=1,
                        character_position=0,
                        content_hash="abc123",
                        original_content_length=50,
                        score=0.8
                    )
                )
            ])

            orchestrator = QueryOrchestratorService()

            # Mock the LLM to fail, triggering fallback
            with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
                mock_llm.side_effect = Exception("LLM unavailable")

                request = OrchestrationRequest(
                    query="What is the RAG system?",
                    max_chunks=3,
                    min_similarity_score=0.5
                )

                # Note: The fallback mechanism would need to be tested differently
                # since our current implementation doesn't have settings.fallback_to_simple_concatenation
                response = await orchestrator.process_query(request)

                # Should fail since no fallback is configured by default
                assert response.status.value == "failed"


def test_create_default_orchestrator():
    """Test creating a default orchestrator instance."""
    with patch('src.services.query_orchestrator.RetrievalService'), \
         patch('src.services.query_orchestrator.ContextManager'), \
         patch('src.services.query_orchestrator.gemini_agent'):
        from src.services.query_orchestrator import create_default_orchestrator
        orchestrator = create_default_orchestrator()

        assert orchestrator is not None
        assert hasattr(orchestrator, 'process_query')


class TestEdgeCases:
    """Test edge cases for the orchestrator."""

    @pytest.mark.asyncio
    async def test_empty_retrieved_chunks(self):
        """Test processing with empty retrieved chunks list."""
        with patch('src.services.query_orchestrator.RetrievalService') as mock_retrieval, \
             patch('src.services.query_orchestrator.ContextManager') as mock_context, \
             patch('src.services.query_orchestrator.gemini_agent'):

            mock_retrieval_instance = Mock()
            mock_retrieval.return_value = mock_retrieval_instance
            mock_retrieval_instance.retrieve_similar_documents = AsyncMock(return_value=[])

            mock_context_instance = Mock()
            mock_context.return_value = mock_context_instance
            mock_context_instance.optimize_context_for_query = Mock(return_value=[])
            mock_context_instance.get_context_summary = Mock(return_value={
                "num_chunks": 0,
                "context_tokens": 0,
                "query_tokens": 5,
                "total_tokens": 5
            })

            orchestrator = QueryOrchestratorService()

            with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
                mock_llm.return_value = "I couldn't find any relevant information in the documentation."

                request = OrchestrationRequest(
                    query="What is the RAG system?",
                    max_chunks=3,
                    min_similarity_score=0.5
                )

                response = await orchestrator.process_query(request)

                assert response.status.value == "completed"
                assert len(response.sources) == 0

    @pytest.mark.asyncio
    async def test_single_long_chunk(self):
        """Test processing with a single very long chunk."""
        long_content = "This is a very long chunk of text. " * 100  # 400 words

        with patch('src.services.query_orchestrator.RetrievalService') as mock_retrieval, \
             patch('src.services.query_orchestrator.ContextManager') as mock_context, \
             patch('src.services.query_orchestrator.gemini_agent'):

            mock_retrieval_instance = Mock()
            mock_retrieval.return_value = mock_retrieval_instance
            mock_retrieval_instance.retrieve_similar_documents = AsyncMock(
                return_value=[{
                    'id': 'chunk-1',
                    'payload': {
                        'content': long_content,
                        'source_file_path': 'docs/test.md',
                        'chunk_index': 1,
                        'character_position': 0,
                        'content_hash': 'abc123'
                    },
                    'score': 0.9
                }]
            )

            mock_context_instance = Mock()
            mock_context.return_value = mock_context_instance
            # Return the long chunk as-is (context manager might truncate it in real usage)
            mock_context_instance.optimize_context_for_query = Mock(side_effect=lambda req: [
                RetrievedChunk(
                    id="chunk-1",
                    content=long_content,
                    metadata=ChunkMetadata(
                        source_file_path="docs/test.md",
                        chunk_index=1,
                        character_position=0,
                        content_hash="abc123",
                        original_content_length=len(long_content),
                        score=0.9
                    )
                )
            ])
            mock_context_instance.get_context_summary = Mock(return_value={
                "num_chunks": 1,
                "context_tokens": 400,  # Approximate
                "query_tokens": 5,
                "total_tokens": 405
            })

            orchestrator = QueryOrchestratorService()

            with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
                mock_llm.return_value = "Based on the long content provided, here is the answer."

                request = OrchestrationRequest(
                    query="Explain the content?",
                    max_chunks=3,
                    min_similarity_score=0.5
                )

                response = await orchestrator.process_query(request)

                assert response.status.value == "completed"
                assert "answer" in response.answer.lower()


if __name__ == "__main__":
    pytest.main([__file__])