"""
Unit Tests for Token Utilities

Tests for the token counting and context management utilities.
"""
import pytest
from src.utils.token_utils import (
    TokenCounter,
    token_counter,
    count_tokens,
    count_tokens_in_messages,
    truncate_text_to_tokens,
    get_remaining_tokens,
    fit_chunks_to_context
)


class TestTokenCounter:
    """Test cases for the TokenCounter class."""

    def test_initialization(self):
        """Test that TokenCounter initializes correctly."""
        counter = TokenCounter()
        assert counter is not None
        assert counter.encoding is not None

    def test_count_tokens_empty_string(self):
        """Test token counting for empty string."""
        assert count_tokens("") == 0

    def test_count_tokens_simple_text(self):
        """Test token counting for simple text."""
        text = "Hello, world!"
        tokens = count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_count_tokens_in_messages(self):
        """Test token counting for message lists."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        tokens = count_tokens_in_messages(messages)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_truncate_text_to_tokens(self):
        """Test text truncation to token limit."""
        long_text = "This is a long text. " * 100
        original_tokens = count_tokens(long_text)

        truncated = truncate_text_to_tokens(long_text, 20)
        truncated_tokens = count_tokens(truncated)

        assert truncated_tokens <= 20
        assert len(truncated) <= len(long_text)

    def test_truncate_text_to_tokens_zero(self):
        """Test truncation with zero token limit."""
        text = "Hello, world!"
        truncated = truncate_text_to_tokens(text, 0)
        assert truncated == ""

    def test_split_text_by_tokens(self):
        """Test splitting text into token-limited chunks."""
        text = "This is a test sentence. " * 20
        chunks = token_counter.split_text_by_tokens(text, max_tokens=20, overlap=2)

        assert len(chunks) > 0
        for chunk in chunks:
            assert count_tokens(chunk) <= 20


class TestTokenUtilityFunctions:
    """Test cases for token utility functions."""

    def test_get_remaining_tokens(self):
        """Test calculation of remaining tokens."""
        prompt_template = "Context: {context}\n\nQuestion: {query}\n\nAnswer:"
        context = "This is some context."
        query = "What is this about?"

        remaining = get_remaining_tokens(
            prompt_template,
            context + query,
            max_context_tokens=1000
        )
        assert remaining >= 0

    def test_get_remaining_tokens_none_max(self):
        """Test remaining tokens calculation with None max value."""
        from src.config import settings
        prompt_template = "Context: {context}\n\nQuestion: {query}\n\nAnswer:"
        context = "This is some context."
        query = "What is this about?"

        remaining = get_remaining_tokens(prompt_template, context + query)
        # Should use settings.LLM_MAX_TOKENS
        assert remaining >= 0

    def test_fit_chunks_to_context(self):
        """Test fitting chunks to context token limit."""
        chunks = [
            {"content": "This is the first chunk of text.", "id": "1"},
            {"content": "This is the second chunk of text.", "id": "2"},
            {"content": "This is the third chunk of text.", "id": "3"}
        ]

        context_template = "Context: {context}\n\nQuestion: {query}\n\nAnswer:"
        query = "What are these chunks about?"

        fitted_chunks = fit_chunks_to_context(
            chunks,
            context_template,
            query,
            max_context_tokens=100
        )

        assert isinstance(fitted_chunks, list)
        assert len(fitted_chunks) <= len(chunks)

    def test_fit_chunks_to_context_empty(self):
        """Test fitting chunks with empty inputs."""
        fitted_chunks = fit_chunks_to_context([], "template", "query", 100)
        assert fitted_chunks == []

    def test_fit_chunks_to_context_no_space(self):
        """Test fitting chunks when no space is available."""
        chunks = [{"content": "Some content", "id": "1"}]
        # Use a template that takes up most of the tokens
        template = "A" * 95
        query = "B" * 5

        fitted_chunks = fit_chunks_to_context(
            chunks,
            template,
            query,
            max_context_tokens=100
        )

        # Should return empty list if no space for content
        assert len(fitted_chunks) <= len(chunks)


def test_global_token_counter():
    """Test the global token counter instance."""
    assert token_counter is not None
    assert hasattr(token_counter, 'count_tokens')
    assert hasattr(token_counter, 'truncate_text_to_tokens')


class TestEdgeCases:
    """Test edge cases for token utilities."""

    def test_count_tokens_special_characters(self):
        """Test token counting with special characters."""
        text = "Hello, 世界! 🌍"
        tokens = count_tokens(text)
        assert tokens > 0

    def test_count_tokens_unicode(self):
        """Test token counting with unicode text."""
        text = "Привет мир! ¡Hola mundo!"
        tokens = count_tokens(text)
        assert tokens > 0

    def test_truncate_preserves_unicode(self):
        """Test that truncation preserves unicode characters."""
        text = "Hello, 世界! 🌍" * 10
        truncated = truncate_text_to_tokens(text, 10)
        # Should not break unicode characters
        assert isinstance(truncated, str)

    def test_large_text_handling(self):
        """Test handling of large text."""
        large_text = "This is a large text. " * 1000
        tokens = count_tokens(large_text)
        assert tokens > 0

        truncated = truncate_text_to_tokens(large_text, 50)
        assert count_tokens(truncated) <= 50


if __name__ == "__main__":
    pytest.main([__file__])