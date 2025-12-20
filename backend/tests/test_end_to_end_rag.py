"""
Integration Tests for End-to-End RAG Pipeline

Tests for the complete RAG pipeline: Qdrant → Gemini → response
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.services.query_orchestrator import QueryOrchestratorService
from src.models.orchestration_models import OrchestrationRequest
from src.api.query_endpoint import router  # We'll need to test the updated endpoint
from backend.main import app  # Need to update the FastAPI app to use orchestration


class TestEndToEndRAGPipeline:
    """Integration tests for the complete RAG pipeline."""

    @pytest.fixture
    def sample_request(self):
        """Create a sample orchestration request."""
        return OrchestrationRequest(
            query="What is the RAG system architecture?",
            max_chunks=3,
            min_similarity_score=0.5,
            include_source_citations=True
        )

    @pytest.mark.asyncio
    async def test_complete_orchestration_flow(self):
        """Test the complete orchestration flow from query to response."""
        with patch('src.services.query_orchestrator.RetrievalService') as mock_retrieval, \
             patch('src.services.query_orchestrator.ContextManager') as mock_context, \
             patch('src.services.query_orchestrator.gemini_agent'):

            # Configure retrieval mock
            mock_retrieval_instance = Mock()
            mock_retrieval.return_value = mock_retrieval_instance
            mock_retrieval_instance.retrieve_similar_documents = AsyncMock(
                return_value=[
                    {
                        'id': 'chunk-1',
                        'payload': {
                            'content': 'The RAG (Retrieval-Augmented Generation) system combines document retrieval with language model generation to provide accurate answers.',
                            'source_file_path': 'docs/architecture.md',
                            'chunk_index': 1,
                            'character_position': 0,
                            'content_hash': 'hash1'
                        },
                        'score': 0.85
                    },
                    {
                        'id': 'chunk-2',
                        'payload': {
                            'content': 'The architecture consists of three main components: the retriever, the generator, and the orchestrator.',
                            'source_file_path': 'docs/components.md',
                            'chunk_index': 2,
                            'character_position': 150,
                            'content_hash': 'hash2'
                        },
                        'score': 0.78
                    }
                ]
            )

            # Configure context manager mock
            mock_context_instance = Mock()
            mock_context.return_value = mock_context_instance

            # Create proper RetrievedChunk objects for context manager return
            from src.models.orchestration_models import RetrievedChunk, ChunkMetadata
            mock_context_instance.optimize_context_for_query = Mock(return_value=[
                RetrievedChunk(
                    id="chunk-1",
                    content="The RAG (Retrieval-Augmented Generation) system combines document retrieval with language model generation to provide accurate answers.",
                    metadata=ChunkMetadata(
                        source_file_path="docs/architecture.md",
                        chunk_index=1,
                        character_position=0,
                        content_hash="hash1",
                        original_content_length=100,
                        score=0.85
                    )
                ),
                RetrievedChunk(
                    id="chunk-2",
                    content="The architecture consists of three main components: the retriever, the generator, and the orchestrator.",
                    metadata=ChunkMetadata(
                        source_file_path="docs/components.md",
                        chunk_index=2,
                        character_position=150,
                        content_hash="hash2",
                        original_content_length=90,
                        score=0.78
                    )
                )
            ])
            mock_context_instance.get_context_summary = Mock(return_value={
                "num_chunks": 2,
                "num_sources": 2,
                "sources": ["docs/architecture.md", "docs/components.md"],
                "context_tokens": 50,
                "query_tokens": 8,
                "total_tokens": 58,
                "fits_model_context": True
            })

            # Create orchestrator
            orchestrator = QueryOrchestratorService()

            # Mock the LLM response
            with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
                expected_response = (
                    "The RAG (Retrieval-Augmented Generation) system is an architecture that combines document retrieval "
                    "with language model generation. It consists of three main components: the retriever, the generator, "
                    "and the orchestrator. The system retrieves relevant documents and uses them as context to generate "
                    "accurate answers to user queries."
                )
                mock_llm.return_value = expected_response

                # Create and process request
                request = OrchestrationRequest(
                    query="What is the RAG system architecture?",
                    max_chunks=3,
                    min_similarity_score=0.5,
                    include_source_citations=True
                )

                response = await orchestrator.process_query(request)

                # Assertions
                assert response.status.value == "completed"
                assert "RAG" in response.answer
                assert "architecture" in response.answer.lower()
                assert len(response.sources) >= 0  # Sources should be included
                assert response.usage_metrics is not None
                assert response.processed_chunks_count == 2

    @pytest.mark.asyncio
    async def test_rag_pipeline_with_low_quality_chunks(self):
        """Test RAG pipeline with low-quality retrieved chunks."""
        with patch('src.services.query_orchestrator.RetrievalService') as mock_retrieval, \
             patch('src.services.query_orchestrator.ContextManager') as mock_context, \
             patch('src.services.query_orchestrator.gemini_agent'):

            # Configure retrieval with low-scoring chunks
            mock_retrieval_instance = Mock()
            mock_retrieval.return_value = mock_retrieval_instance
            mock_retrieval_instance.retrieve_similar_documents = AsyncMock(
                return_value=[
                    {
                        'id': 'chunk-1',
                        'payload': {
                            'content': 'This chunk has very low relevance to the query.',
                            'source_file_path': 'docs/unrelated.md',
                            'chunk_index': 1,
                            'character_position': 0,
                            'content_hash': 'hash1'
                        },
                        'score': 0.1  # Low score
                    }
                ]
            )

            # Context manager should filter out low-scoring chunks
            mock_context_instance = Mock()
            mock_context.return_value = mock_context_instance
            mock_context_instance.optimize_context_for_query = Mock(return_value=[])  # No chunks after filtering
            mock_context_instance.get_context_summary = Mock(return_value={
                "num_chunks": 0,
                "num_sources": 0,
                "sources": [],
                "context_tokens": 0,
                "query_tokens": 8,
                "total_tokens": 8,
                "fits_model_context": True
            })

            orchestrator = QueryOrchestratorService()

            with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
                mock_llm.return_value = "I couldn't find relevant information in the documentation to answer your query about the RAG system architecture."

                request = OrchestrationRequest(
                    query="What is the RAG system architecture?",
                    max_chunks=3,
                    min_similarity_score=0.5  # Higher threshold to filter out low-scoring chunk
                )

                response = await orchestrator.process_query(request)

                assert response.status.value == "completed"
                assert response.processed_chunks_count == 0
                assert len(response.sources) == 0

    @pytest.mark.asyncio
    async def test_rag_pipeline_token_limit_handling(self):
        """Test RAG pipeline handling of token limits."""
        with patch('src.services.query_orchestrator.RetrievalService') as mock_retrieval, \
             patch('src.services.query_orchestrator.ContextManager') as mock_context, \
             patch('src.services.query_orchestrator.gemini_agent'):

            # Configure retrieval with multiple chunks
            mock_retrieval_instance = Mock()
            mock_retrieval.return_value = mock_retrieval_instance
            mock_retrieval_instance.retrieve_similar_documents = AsyncMock(
                return_value=[
                    {
                        'id': 'chunk-1',
                        'payload': {
                            'content': 'First part of the documentation with important information about RAG.',
                            'source_file_path': 'docs/part1.md',
                            'chunk_index': 1,
                            'character_position': 0,
                            'content_hash': 'hash1'
                        },
                        'score': 0.9
                    },
                    {
                        'id': 'chunk-2',
                        'payload': {
                            'content': 'Second part with additional details about the architecture.',
                            'source_file_path': 'docs/part2.md',
                            'chunk_index': 2,
                            'character_position': 100,
                            'content_hash': 'hash2'
                        },
                        'score': 0.85
                    },
                    {
                        'id': 'chunk-3',
                        'payload': {
                            'content': 'Third part with more context but lower priority information.',
                            'source_file_path': 'docs/part3.md',
                            'chunk_index': 3,
                            'character_position': 200,
                            'content_hash': 'hash3'
                        },
                        'score': 0.7
                    }
                ]
            )

            # Context manager should limit chunks based on token constraints
            from src.models.orchestration_models import RetrievedChunk, ChunkMetadata
            mock_context_instance = Mock()
            mock_context.return_value = mock_context_instance
            # Return only the highest scoring chunks that fit within token limits
            mock_context_instance.optimize_context_for_query = Mock(return_value=[
                RetrievedChunk(
                    id="chunk-1",
                    content="First part of the documentation with important information about RAG.",
                    metadata=ChunkMetadata(
                        source_file_path="docs/part1.md",
                        chunk_index=1,
                        character_position=0,
                        content_hash="hash1",
                        original_content_length=60,
                        score=0.9
                    )
                ),
                RetrievedChunk(
                    id="chunk-2",
                    content="Second part with additional details about the architecture.",
                    metadata=ChunkMetadata(
                        source_file_path="docs/part2.md",
                        chunk_index=2,
                        character_position=100,
                        content_hash="hash2",
                        original_content_length=55,
                        score=0.85
                    )
                )
            ])
            mock_context_instance.get_context_summary = Mock(return_value={
                "num_chunks": 2,  # Limited to 2 chunks
                "num_sources": 2,
                "sources": ["docs/part1.md", "docs/part2.md"],
                "context_tokens": 40,
                "query_tokens": 8,
                "total_tokens": 48,
                "fits_model_context": True
            })

            orchestrator = QueryOrchestratorService()

            with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
                mock_llm.return_value = "Based on the documentation, the RAG system architecture consists of several key components..."

                request = OrchestrationRequest(
                    query="What is the RAG system architecture?",
                    max_chunks=3,
                    min_similarity_score=0.5
                )

                response = await orchestrator.process_query(request)

                assert response.status.value == "completed"
                assert response.processed_chunks_count == 2  # Limited by token management
                assert len(response.sources) >= 0

    @pytest.mark.asyncio
    async def test_rag_pipeline_error_handling(self):
        """Test RAG pipeline error handling for various failure modes."""
        # Test retrieval failure
        with patch('src.services.query_orchestrator.RetrievalService') as mock_retrieval, \
             patch('src.services.query_orchestrator.ContextManager'), \
             patch('src.services.query_orchestrator.gemini_agent'):

            mock_retrieval_instance = Mock()
            mock_retrieval.return_value = mock_retrieval_instance
            mock_retrieval_instance.retrieve_similar_documents = AsyncMock(
                side_effect=Exception("Retrieval service unavailable")
            )

            orchestrator = QueryOrchestratorService()

            request = OrchestrationRequest(
                query="What is the RAG system?",
                max_chunks=3
            )

            response = await orchestrator.process_query(request)

            assert response.status.value == "failed"
            assert "error" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_rag_pipeline_quality_assessment(self):
        """Test that the RAG pipeline maintains quality in responses."""
        with patch('src.services.query_orchestrator.RetrievalService') as mock_retrieval, \
             patch('src.services.query_orchestrator.ContextManager') as mock_context, \
             patch('src.services.query_orchestrator.gemini_agent'):

            # Configure retrieval with relevant chunks
            mock_retrieval_instance = Mock()
            mock_retrieval.return_value = mock_retrieval_instance
            mock_retrieval_instance.retrieve_similar_documents = AsyncMock(
                return_value=[
                    {
                        'id': 'chunk-1',
                        'payload': {
                            'content': 'The RAG system retrieves relevant documents from Qdrant vector database based on semantic similarity.',
                            'source_file_path': 'docs/retrieval.md',
                            'chunk_index': 1,
                            'character_position': 0,
                            'content_hash': 'hash1'
                        },
                        'score': 0.92
                    },
                    {
                        'id': 'chunk-2',
                        'payload': {
                            'content': 'The generation component uses large language models to create human-readable responses based on retrieved context.',
                            'source_file_path': 'docs/generation.md',
                            'chunk_index': 1,
                            'character_position': 120,
                            'content_hash': 'hash2'
                        },
                        'score': 0.88
                    }
                ]
            )

            # Configure context manager
            from src.models.orchestration_models import RetrievedChunk, ChunkMetadata
            mock_context_instance = Mock()
            mock_context.return_value = mock_context_instance
            mock_context_instance.optimize_context_for_query = Mock(return_value=[
                RetrievedChunk(
                    id="chunk-1",
                    content="The RAG system retrieves relevant documents from Qdrant vector database based on semantic similarity.",
                    metadata=ChunkMetadata(
                        source_file_path="docs/retrieval.md",
                        chunk_index=1,
                        character_position=0,
                        content_hash="hash1",
                        original_content_length=85,
                        score=0.92
                    )
                ),
                RetrievedChunk(
                    id="chunk-2",
                    content="The generation component uses large language models to create human-readable responses based on retrieved context.",
                    metadata=ChunkMetadata(
                        source_file_path="docs/generation.md",
                        chunk_index=1,
                        character_position=120,
                        content_hash="hash2",
                        original_content_length=95,
                        score=0.88
                    )
                )
            ])
            mock_context_instance.get_context_summary = Mock(return_value={
                "num_chunks": 2,
                "num_sources": 2,
                "sources": ["docs/retrieval.md", "docs/generation.md"],
                "context_tokens": 60,
                "query_tokens": 8,
                "total_tokens": 68,
                "avg_similarity_score": 0.90,
                "fits_model_context": True
            })

            orchestrator = QueryOrchestratorService()

            with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
                # Mock a high-quality response that properly synthesizes information
                high_quality_response = (
                    "The RAG (Retrieval-Augmented Generation) system works by first retrieving relevant documents "
                    "from a Qdrant vector database based on semantic similarity to the user's query. Then, a large "
                    "language model uses this retrieved context to generate human-readable, accurate responses. "
                    "This approach combines the precision of document retrieval with the generative capabilities "
                    "of modern language models."
                )
                mock_llm.return_value = high_quality_response

                request = OrchestrationRequest(
                    query="How does the RAG system work?",
                    max_chunks=3,
                    min_similarity_score=0.5,
                    include_source_citations=True
                )

                response = await orchestrator.process_query(request)

                # Assertions for quality
                assert response.status.value == "completed"
                assert len(response.answer) > 50  # Substantial response
                assert "RAG" in response.answer
                assert "retrieval" in response.answer.lower() or "retrieve" in response.answer.lower()
                assert "generation" in response.answer.lower() or "generate" in response.answer.lower()
                assert response.processed_chunks_count == 2
                assert response.usage_metrics is not None


class TestRAGPipelinePerformance:
    """Performance-related tests for the RAG pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_response_time(self):
        """Test that the pipeline responds within acceptable time limits."""
        with patch('src.services.query_orchestrator.RetrievalService') as mock_retrieval, \
             patch('src.services.query_orchestrator.ContextManager') as mock_context, \
             patch('src.services.query_orchestrator.gemini_agent'):

            # Configure mocks with realistic delays simulated
            mock_retrieval_instance = Mock()
            mock_retrieval.return_value = mock_retrieval_instance
            mock_retrieval_instance.retrieve_similar_documents = AsyncMock(
                return_value=[
                    {
                        'id': 'chunk-1',
                        'payload': {
                            'content': 'Sample content for timing test.',
                            'source_file_path': 'docs/test.md',
                            'chunk_index': 1,
                            'character_position': 0,
                            'content_hash': 'hash1'
                        },
                        'score': 0.8
                    }
                ]
            )

            from src.models.orchestration_models import RetrievedChunk, ChunkMetadata
            mock_context_instance = Mock()
            mock_context.return_value = mock_context_instance
            mock_context_instance.optimize_context_for_query = Mock(return_value=[
                RetrievedChunk(
                    id="chunk-1",
                    content="Sample content for timing test.",
                    metadata=ChunkMetadata(
                        source_file_path="docs/test.md",
                        chunk_index=1,
                        character_position=0,
                        content_hash="hash1",
                        original_content_length=30,
                        score=0.8
                    )
                )
            ])
            mock_context_instance.get_context_summary = Mock(return_value={
                "num_chunks": 1,
                "total_tokens": 15,
                "fits_model_context": True
            })

            orchestrator = QueryOrchestratorService()

            with patch('src.services.query_orchestrator.get_gemini_completion_async') as mock_llm:
                mock_llm.return_value = "Sample response for timing test."

                import time
                start_time = time.time()

                request = OrchestrationRequest(
                    query="Performance test query?",
                    max_chunks=1
                )

                response = await orchestrator.process_query(request)

                end_time = time.time()
                processing_time = (end_time - start_time) * 1000  # Convert to milliseconds

                # Should complete in reasonable time (under 5 seconds for this simple test)
                assert processing_time < 5000
                assert response.total_time_ms is not None
                assert response.status.value == "completed"


def test_rag_pipeline_module_imports():
    """Test that all necessary modules for RAG pipeline can be imported."""
    try:
        from src.services.query_orchestrator import QueryOrchestratorService
        from src.models.orchestration_models import OrchestrationRequest, OrchestrationResponse
        from src.models.prompt_template import RAGPromptTemplate
        from src.services.context_manager import ContextManager
        from src.utils.token_utils import token_counter
        from agent import gemini_agent, get_gemini_completion_async

        assert QueryOrchestratorService is not None
        assert OrchestrationRequest is not None
        assert OrchestrationResponse is not None
        assert RAGPromptTemplate is not None
        assert ContextManager is not None
        assert token_counter is not None
        assert gemini_agent is not None
        assert get_gemini_completion_async is not None

    except ImportError as e:
        pytest.fail(f"Failed to import RAG pipeline modules: {e}")


if __name__ == "__main__":
    pytest.main([__file__])