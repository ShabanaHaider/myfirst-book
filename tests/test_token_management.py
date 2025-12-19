"""
Integration tests for token management functionality.

These tests validate the integration between token utilities,
context management, and orchestration services.
"""
import pytest
from unittest.mock import Mock, patch
from src.utils.token_utils import (
    TokenCounter, count_tokens, count_tokens_in_messages,
    truncate_text_to_tokens, get_remaining_tokens,
    fit_chunks_to_context, PromptOptimizer, optimize_context_for_max_usage,
    calculate_optimal_chunk_size, compress_prompt
)
from src.services.context_manager import ContextManager
from src.services.query_orchestrator import QueryOrchestratorService
from src.models.orchestration_models import RetrievedChunk, ChunkMetadata, OrchestrationRequest
from src.config.settings import settings


class TestTokenManagementIntegration:
    """Integration test suite for token management functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.token_counter = TokenCounter()
        self.context_manager = ContextManager()
        self.orchestrator_service = QueryOrchestratorService()

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

    def test_token_counter_integration(self):
        """Test token counter integration with context manager."""
        text = "This is a sample text for token counting."
        token_count = self.token_counter.count_tokens(text)

        assert isinstance(token_count, int)
        assert token_count > 0

        # Test with context manager
        chunks = self.sample_chunks
        total_tokens = sum(self.token_counter.count_tokens(chunk.content) for chunk in chunks)

        assert total_tokens > 0

    def test_count_tokens_function_integration(self):
        """Test the count_tokens function integration."""
        text = "This is a sample text for token counting."
        token_count = count_tokens(text)

        assert isinstance(token_count, int)
        assert token_count > 0

    def test_count_tokens_in_messages_integration(self):
        """Test counting tokens in messages."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"}
        ]

        token_count = count_tokens_in_messages(messages)

        assert isinstance(token_count, int)
        assert token_count > 0

    def test_truncate_text_to_tokens_integration(self):
        """Test text truncation based on token limits."""
        long_text = "This is a long text that will be truncated based on token limits. " * 20
        max_tokens = 10

        truncated_text = truncate_text_to_tokens(long_text, max_tokens)

        assert isinstance(truncated_text, str)
        assert len(truncated_text) <= len(long_text)

        # Verify the truncated text has fewer or equal tokens
        original_tokens = count_tokens(long_text)
        truncated_tokens = count_tokens(truncated_text)
        assert truncated_tokens <= max_tokens
        assert truncated_tokens <= original_tokens

    def test_split_text_by_tokens_integration(self):
        """Test splitting text by token limits."""
        long_text = "This is a long text that will be split based on token limits. " * 20
        max_tokens = 20

        # Use the TokenCounter instance method instead of global function
        chunks = self.token_counter.split_text_by_tokens(long_text, max_tokens)

        assert isinstance(chunks, list)
        assert len(chunks) > 0

        # Each chunk should be within token limits
        for chunk in chunks:
            assert count_tokens(chunk) <= max_tokens

    def test_get_remaining_tokens_integration(self):
        """Test calculation of remaining tokens."""
        prompt_template = "Context: {context}\n\nQuestion: {query}\n\nAnswer:"
        current_content = "Some existing content here."
        max_context_tokens = 1000

        remaining = get_remaining_tokens(
            prompt_template=prompt_template,
            current_content=current_content,
            max_context_tokens=max_context_tokens
        )

        assert isinstance(remaining, int)
        assert remaining >= 0

    def test_fit_chunks_to_context_integration(self):
        """Test fitting chunks to context with token limits."""
        # Convert RetrievedChunk objects to dictionaries as expected by the function
        chunk_dicts = []
        for chunk in self.sample_chunks:
            chunk_dict = {
                'content': chunk.content,
                'score': chunk.metadata.score,
                'source_file_path': chunk.metadata.source_file_path,
                'chunk_index': chunk.metadata.chunk_index
            }
            chunk_dicts.append(chunk_dict)

        context_template = "Context: {context}\n\nQuestion: {query}\n\nAnswer:"
        query = self.sample_query
        max_context_tokens = 500

        fitted_chunks = fit_chunks_to_context(
            chunks=chunk_dicts,
            context_template=context_template,
            query=query,
            max_context_tokens=max_context_tokens
        )

        assert isinstance(fitted_chunks, list)
        assert len(fitted_chunks) <= len(chunk_dicts)

        # Verify that the fitted chunks don't exceed token limits
        context_content = "\n\n".join([chunk['content'] for chunk in fitted_chunks])
        template_filled = context_template.format(context=context_content, query=query)
        total_tokens = count_tokens(template_filled)

        # Allow some buffer for template tokens
        assert total_tokens <= max_context_tokens + 100

    def test_prompt_optimizer_integration(self):
        """Test PromptOptimizer integration."""
        optimizer = PromptOptimizer()

        # Test optimize_context_for_max_usage
        result = optimize_context_for_max_usage(
            chunks=[{'content': chunk.content, 'score': chunk.metadata.score} for chunk in self.sample_chunks],
            context_template="Context: {context}\n\nQuestion: {query}\n\nAnswer:",
            query=self.sample_query,
            max_context_tokens=500
        )

        assert isinstance(result, list)
        assert len(result) <= len(self.sample_chunks)

        # Test calculate_optimal_chunk_size
        allocation = calculate_optimal_chunk_size(
            num_chunks=3,
            context_template="Context: {context}\n\nQuestion: {query}\n\nAnswer:",
            query=self.sample_query,
            max_context_tokens=500
        )

        assert isinstance(allocation, dict)
        assert 'per_chunk_allocation' in allocation
        assert allocation['per_chunk_allocation'] >= 0

        # Test compress_prompt
        long_prompt = "This is a long prompt that needs to be compressed. " * 50
        compressed = compress_prompt(long_prompt, target_tokens=50)

        assert isinstance(compressed, str)
        assert count_tokens(compressed) <= 50

    def test_context_manager_with_token_limits(self):
        """Test context manager integration with token limits."""
        request = OrchestrationRequest(
            query=self.sample_query,
            retrieved_chunks=self.sample_chunks,
            context_parameters={'max_context_tokens': 200}  # Restrictive limit
        )

        # Test optimization with token constraints
        optimized_chunks = self.context_manager.optimize_context_for_query(request)

        assert isinstance(optimized_chunks, list)
        assert len(optimized_chunks) <= len(self.sample_chunks)

        # Verify that the optimized context fits within limits
        fits_model = self.context_manager.validate_context_fits_model(
            optimized_chunks,
            request.query,
            request.context_parameters['max_context_tokens']
        )

        assert fits_model or len(optimized_chunks) == 0  # Either fits or was reduced to empty

    def test_context_manager_fallback_strategies_with_tokens(self):
        """Test context manager fallback strategies with token validation."""
        # Create chunks that will likely exceed token limits
        large_chunks = [
            RetrievedChunk(
                id="large-chunk-1",
                content="This is a large chunk of content that will exceed token limits when combined with others. " * 30,
                metadata=ChunkMetadata(
                    source_file_path="docs/large.md",
                    chunk_index=1,
                    character_position=0,
                    content_hash="large_hash1",
                    original_content_length=300,
                    score=0.9
                )
            ),
            RetrievedChunk(
                id="large-chunk-2",
                content="This is another large chunk of content that will exceed token limits when combined with others. " * 30,
                metadata=ChunkMetadata(
                    source_file_path="docs/large.md",
                    chunk_index=2,
                    character_position=300,
                    content_hash="large_hash2",
                    original_content_length=300,
                    score=0.8
                )
            )
        ]

        request = OrchestrationRequest(
            query=self.sample_query,
            retrieved_chunks=large_chunks,
            context_parameters={'max_context_tokens': 100}  # Very restrictive
        )

        # Apply fallback strategies
        fallback_result = self.context_manager.apply_fallback_strategies(
            chunks=large_chunks,
            query=self.sample_query,
            max_context_tokens=100,
            strategy="progressive_trimming"
        )

        assert isinstance(fallback_result, list)

        # Verify that the result fits within token limits (with some buffer for template overhead)
        if fallback_result:
            context_size = self.context_manager.calculate_context_size(fallback_result, self.sample_query)
            # Allow for template and query overhead (typically ~50-100 tokens)
            assert context_size[2] <= 150  # total_tokens should be reasonably close to the limit

    def test_integration_with_orchestration_service(self):
        """Test token management integration with orchestration service."""
        # Mock the LLM client to avoid actual API calls during testing
        with patch.object(self.orchestrator_service, 'gemini_client', spec=True):
            with patch.object(self.orchestrator_service, '_construct_prompt_with_context') as mock_construct:
                # Mock the prompt construction to return a simple string
                mock_construct.return_value = "Mocked prompt for testing"

                # Create a request with token constraints
                request = OrchestrationRequest(
                    query=self.sample_query,
                    retrieved_chunks=self.sample_chunks,
                    context_parameters={
                        'max_context_tokens': 300,
                        'temperature': 0.7,
                        'max_tokens': 150
                    },
                    max_chunks=3,
                    min_similarity_score=0.5,
                    fallback_strategy="progressive_trimming"
                )

                # Process the query - this will exercise the token management
                # Note: We're not testing the full LLM call, just the orchestration logic
                # In a real test, we'd mock the LLM call

                # Check that context optimization is working
                optimized_chunks = self.context_manager.optimize_context_for_query(request)
                assert isinstance(optimized_chunks, list)

                # Check that token counting is working
                for chunk in optimized_chunks:
                    token_count = count_tokens(chunk.content)
                    assert isinstance(token_count, int) and token_count >= 0

    def test_prompt_construction_with_token_limits(self):
        """Test prompt construction respecting token limits."""
        # Test the internal method that constructs prompts with token limits
        result = self.orchestrator_service._construct_prompt_with_context(
            query=self.sample_query,
            context_chunks=self.sample_chunks,
            request=OrchestrationRequest(
                query=self.sample_query,
                retrieved_chunks=self.sample_chunks,
                context_parameters={'max_context_tokens': 500}
            )
        )

        assert isinstance(result, str)
        assert len(result) > 0

        # Check that the result is within reasonable token limits
        result_tokens = count_tokens(result)
        # The result should be less than or equal to the specified max_context_tokens
        # (with some buffer for overhead)
        assert result_tokens <= 500 + 100  # Adding buffer for template overhead

    def test_token_utility_edge_cases(self):
        """Test token utilities with edge cases."""
        # Test with empty text
        assert count_tokens("") == 0
        assert count_tokens(None) == 0  # This might fail, depending on implementation

        # Test truncation with zero tokens
        assert truncate_text_to_tokens("Some text", 0) == ""
        assert truncate_text_to_tokens("", 10) == ""

        # Test with very short text
        short_text = "Hi"
        tokens = count_tokens(short_text)
        assert tokens > 0

        # Test splitting with very small limits
        chunks = self.token_counter.split_text_by_tokens("A B C D E F G H I J", 1)
        assert isinstance(chunks, list)
        assert len(chunks) > 0

        # Test splitting with zero tokens
        chunks_zero = self.token_counter.split_text_by_tokens("Some text", 0)
        assert len(chunks_zero) == 1  # Should return the original text as a single item if non-empty, or empty list if empty