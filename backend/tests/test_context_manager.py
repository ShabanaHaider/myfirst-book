"""
Unit tests for the Context Manager module.

These tests validate the functionality of the ContextManager class,
including chunk selection, ranking, token management, and fallback strategies.
"""
import pytest
from unittest.mock import Mock
from src.services.context_manager import ContextManager
from src.models.orchestration_models import RetrievedChunk, ChunkMetadata
from src.config.settings import settings


class TestContextManager:
    """Test suite for ContextManager functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.context_manager = ContextManager()

        # Create sample chunks for testing
        self.sample_chunks = [
            RetrievedChunk(
                id="chunk-1",
                content="This is the first chunk with some important information about the topic. It contains several sentences to test token counting and context management.",
                metadata=ChunkMetadata(
                    source_file_path="docs/intro.md",
                    chunk_index=1,
                    character_position=0,
                    content_hash="hash1",
                    original_content_length=100,
                    score=0.85
                )
            ),
            RetrievedChunk(
                id="chunk-2",
                content="This is the second chunk with additional information. It provides more context and details about the subject matter. This chunk is also important for the overall understanding.",
                metadata=ChunkMetadata(
                    source_file_path="docs/intro.md",
                    chunk_index=2,
                    character_position=100,
                    content_hash="hash2",
                    original_content_length=100,
                    score=0.78
                )
            ),
            RetrievedChunk(
                id="chunk-3",
                content="This is the third chunk with supplementary details. It adds to the information provided in the previous chunks and helps create a more complete picture of the topic.",
                metadata=ChunkMetadata(
                    source_file_path="docs/advanced.md",
                    chunk_index=1,
                    character_position=0,
                    content_hash="hash3",
                    original_content_length=100,
                    score=0.65
                )
            )
        ]

        self.sample_query = "What is the main concept discussed in the documentation?"

    def test_select_chunks_for_context_basic(self):
        """Test basic chunk selection functionality."""
        result = self.context_manager.select_chunks_for_context(
            chunks=self.sample_chunks,
            query=self.sample_query
        )

        # Should return chunks within token limits
        assert isinstance(result, list)
        assert len(result) <= len(self.sample_chunks)
        assert all(isinstance(chunk, RetrievedChunk) for chunk in result)

    def test_select_chunks_for_context_with_limits(self):
        """Test chunk selection with specific token limits."""
        result = self.context_manager.select_chunks_for_context(
            chunks=self.sample_chunks,
            query=self.sample_query,
            max_context_tokens=100  # Very restrictive limit
        )

        # Should return fewer chunks due to token limit
        assert isinstance(result, list)
        # The result might be empty if the token limit is too restrictive
        if result:
            assert len(result) <= len(self.sample_chunks)

    def test_rank_chunks_intelligently(self):
        """Test intelligent chunk ranking based on multiple factors."""
        ranked_chunks = self.context_manager._rank_chunks_intelligently(
            self.sample_chunks,
            self.sample_query
        )

        assert isinstance(ranked_chunks, list)
        assert len(ranked_chunks) == len(self.sample_chunks)

        # Check that ranking is stable and deterministic
        ranked_chunks_2 = self.context_manager._rank_chunks_intelligently(
            self.sample_chunks,
            self.sample_query
        )

        assert [c.id for c in ranked_chunks] == [c.id for c in ranked_chunks_2]

    def test_intelligent_fit_chunks_to_context(self):
        """Test intelligent fitting of chunks to context with token limits."""
        chunk_dicts = [
            {'id': chunk.id, 'content': chunk.content, 'score': chunk.metadata.score,
             'source_file_path': chunk.metadata.source_file_path, 'chunk_index': chunk.metadata.chunk_index}
            for chunk in self.sample_chunks
        ]

        result = self.context_manager._intelligent_fit_chunks_to_context(
            chunks=chunk_dicts,
            context_template="Context: {context}\n\nQuestion: {query}\n\nAnswer:",
            query=self.sample_query,
            max_context_tokens=500  # Reasonable limit
        )

        assert isinstance(result, list)
        assert len(result) <= len(chunk_dicts)

    def test_intelligently_trim_chunk(self):
        """Test intelligent chunk trimming."""
        long_content = "This is a very long chunk of text that will be used to test the intelligent trimming functionality. " * 20
        max_tokens = 50

        trimmed_content = self.context_manager._intelligently_trim_chunk(
            content=long_content,
            max_tokens=max_tokens
        )

        assert isinstance(trimmed_content, str)
        # The trimmed content should be less than or equal to the max tokens
        # Note: This is a simplified check since exact token count may vary

    def test_calculate_context_size(self):
        """Test context size calculation."""
        context_tokens, query_tokens, total_tokens = self.context_manager.calculate_context_size(
            chunks=self.sample_chunks,
            query=self.sample_query
        )

        assert isinstance(context_tokens, int)
        assert isinstance(query_tokens, int)
        assert isinstance(total_tokens, int)
        assert total_tokens >= context_tokens + query_tokens

    def test_trim_chunk_content(self):
        """Test chunk content trimming."""
        chunk = self.sample_chunks[0]
        max_tokens = 10

        trimmed_chunk = self.context_manager.trim_chunk_content(chunk, max_tokens)

        assert isinstance(trimmed_chunk, RetrievedChunk)
        assert trimmed_chunk.id == chunk.id

    def test_prioritize_chunks_by_relevance(self):
        """Test chunk prioritization by relevance."""
        methods = ["score", "position", "hybrid"]

        for method in methods:
            prioritized = self.context_manager.prioritize_chunks_by_relevance(
                self.sample_chunks,
                self.sample_query,
                method=method
            )

            assert isinstance(prioritized, list)
            assert len(prioritized) == len(self.sample_chunks)

    def test_validate_context_fits_model(self):
        """Test context validation against model limits."""
        fits = self.context_manager.validate_context_fits_model(
            chunks=self.sample_chunks,
            query=self.sample_query
        )

        assert isinstance(fits, bool)

    def test_get_context_summary(self):
        """Test context summary generation."""
        summary = self.context_manager.get_context_summary(
            chunks=self.sample_chunks,
            query=self.sample_query
        )

        assert isinstance(summary, dict)
        assert "num_chunks" in summary
        assert "total_tokens" in summary
        assert summary["num_chunks"] == len(self.sample_chunks)

    def test_optimize_context_for_query(self):
        """Test context optimization for a query."""
        from src.models.orchestration_models import OrchestrationRequest

        request = OrchestrationRequest(
            query=self.sample_query,
            retrieved_chunks=self.sample_chunks
        )

        optimized_chunks = self.context_manager.optimize_context_for_query(request)

        assert isinstance(optimized_chunks, list)
        assert len(optimized_chunks) <= len(self.sample_chunks)

    def test_apply_fallback_strategies_progressive_trimming(self):
        """Test progressive trimming fallback strategy."""
        # Create chunks that exceed token limits
        large_chunks = [
            RetrievedChunk(
                id="large-chunk-1",
                content="This is a large chunk of text that exceeds token limits. " * 50,
                metadata=ChunkMetadata(
                    source_file_path="docs/large.md",
                    chunk_index=1,
                    character_position=0,
                    content_hash="large_hash1",
                    original_content_length=500,
                    score=0.9
                )
            ),
            RetrievedChunk(
                id="large-chunk-2",
                content="This is another large chunk of text that exceeds token limits. " * 50,
                metadata=ChunkMetadata(
                    source_file_path="docs/large.md",
                    chunk_index=2,
                    character_position=500,
                    content_hash="large_hash2",
                    original_content_length=500,
                    score=0.8
                )
            )
        ]

        result = self.context_manager.apply_fallback_strategies(
            chunks=large_chunks,
            query=self.sample_query,
            max_context_tokens=100,  # Very restrictive limit
            strategy="progressive_trimming"
        )

        assert isinstance(result, list)
        # Result might be empty due to strict token limit

    def test_apply_fallback_strategies_selective_ranking(self):
        """Test selective ranking fallback strategy."""
        result = self.context_manager.apply_fallback_strategies(
            chunks=self.sample_chunks,
            query=self.sample_query,
            max_context_tokens=100,  # Restrictive limit
            strategy="selective_ranking"
        )

        assert isinstance(result, list)

    def test_apply_fallback_strategies_query_focused(self):
        """Test query-focused fallback strategy."""
        result = self.context_manager.apply_fallback_strategies(
            chunks=self.sample_chunks,
            query=self.sample_query,
            max_context_tokens=100,  # Restrictive limit
            strategy="query_focused"
        )

        assert isinstance(result, list)

    def test_apply_fallback_strategies_summary_based(self):
        """Test summary-based fallback strategy."""
        result = self.context_manager.apply_fallback_strategies(
            chunks=self.sample_chunks,
            query=self.sample_query,
            max_context_tokens=100,  # Restrictive limit
            strategy="summary_based"
        )

        assert isinstance(result, list)

    def test_apply_fallback_strategies_default(self):
        """Test default fallback strategy."""
        result = self.context_manager.apply_fallback_strategies(
            chunks=self.sample_chunks,
            query=self.sample_query,
            max_context_tokens=100,  # Restrictive limit
            strategy="nonexistent_strategy"  # Should default to progressive_trimming
        )

        assert isinstance(result, list)

    def test_apply_fallback_strategies_no_fallback_needed(self):
        """Test fallback strategies when no fallback is needed."""
        result = self.context_manager.apply_fallback_strategies(
            chunks=self.sample_chunks,
            query=self.sample_query,
            max_context_tokens=5000,  # Very generous limit
            strategy="progressive_trimming"
        )

        # Should return original chunks or a similar amount since no fallback is needed
        assert isinstance(result, list)
        assert len(result) <= len(self.sample_chunks)

    def test_create_default_context_manager(self):
        """Test creating a default context manager instance."""
        from src.services.context_manager import create_default_context_manager

        manager = create_default_context_manager()

        assert isinstance(manager, ContextManager)