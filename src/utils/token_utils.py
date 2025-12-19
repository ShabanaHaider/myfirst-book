"""
Token Utilities for Context Management

This module provides utilities for counting tokens and managing context size
to ensure prompts fit within model constraints.
"""
import tiktoken
from typing import List, Dict, Any
from src.config.settings import settings


class TokenCounter:
    """
    Utility class for counting tokens in text content.
    Uses tiktoken which is compatible with OpenAI models and provides
    a good approximation for other models like Gemini.
    """

    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize the token counter with a specific encoding.

        Args:
            encoding_name: The name of the encoding to use (default: cl100k_base for GPT-4/GPT-3.5-turbo)
        """
        self.encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a given text.

        Args:
            text: The text to count tokens for

        Returns:
            The number of tokens in the text
        """
        if not text:
            return 0

        return len(self.encoding.encode(text))

    def count_tokens_in_messages(self, messages: List[Dict[str, str]]) -> int:
        """
        Count the number of tokens in a list of messages (role/content pairs).

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys

        Returns:
            The total number of tokens in all messages
        """
        total_tokens = 0

        for message in messages:
            if 'role' in message:
                total_tokens += self.count_tokens(message['role'])
            if 'content' in message:
                total_tokens += self.count_tokens(str(message['content']))

        # Account for message formatting overhead
        total_tokens += len(messages) * 3  # For role, content, and message separators

        return total_tokens

    def truncate_text_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within a maximum number of tokens.

        Args:
            text: The text to truncate
            max_tokens: The maximum number of tokens allowed

        Returns:
            The truncated text that fits within the token limit
        """
        if not text or max_tokens <= 0:
            return ""

        tokens = self.encoding.encode(text)

        if len(tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[:max_tokens]
        truncated_text = self.encoding.decode(truncated_tokens)

        return truncated_text

    def split_text_by_tokens(self, text: str, max_tokens: int, overlap: int = 0) -> List[str]:
        """
        Split text into chunks that fit within a token limit.

        Args:
            text: The text to split
            max_tokens: Maximum tokens per chunk
            overlap: Number of overlapping tokens between chunks

        Returns:
            List of text chunks that fit within the token limit
        """
        if not text or max_tokens <= 0:
            return [text] if text else []

        tokens = self.encoding.encode(text)

        if len(tokens) <= max_tokens:
            return [text]

        chunks = []
        start_idx = 0

        while start_idx < len(tokens):
            end_idx = start_idx + max_tokens
            chunk_tokens = tokens[start_idx:end_idx]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

            if end_idx >= len(tokens):
                break

            # Move start index forward, accounting for overlap
            start_idx = end_idx - overlap
            if overlap > 0 and start_idx <= start_idx + overlap:
                start_idx = start_idx + 1  # Ensure we make progress

        return chunks


# Global token counter instance
token_counter = TokenCounter()


def count_tokens(text: str) -> int:
    """
    Count tokens in text using the global token counter.

    Args:
        text: The text to count tokens for

    Returns:
        The number of tokens in the text
    """
    return token_counter.count_tokens(text)


def count_tokens_in_messages(messages: List[Dict[str, str]]) -> int:
    """
    Count tokens in messages using the global token counter.

    Args:
        messages: List of message dictionaries with 'role' and 'content' keys

    Returns:
        The total number of tokens in all messages
    """
    return token_counter.count_tokens_in_messages(messages)


def truncate_text_to_tokens(text: str, max_tokens: int) -> str:
    """
    Truncate text to fit within a maximum number of tokens.

    Args:
        text: The text to truncate
        max_tokens: The maximum number of tokens allowed

    Returns:
        The truncated text that fits within the token limit
    """
    return token_counter.truncate_text_to_tokens(text, max_tokens)


def get_remaining_tokens(prompt_template: str, current_content: str,
                        max_context_tokens: int = None) -> int:
    """
    Calculate how many tokens remain available in a context.

    Args:
        prompt_template: The template for the prompt
        current_content: Current content that will be part of the prompt
        max_context_tokens: Maximum context tokens (defaults to settings.LLM_MAX_TOKENS)

    Returns:
        Number of tokens remaining in the context
    """
    if max_context_tokens is None:
        max_context_tokens = settings.LLM_MAX_TOKENS

    used_tokens = count_tokens(prompt_template) + count_tokens(current_content)
    remaining = max_context_tokens - used_tokens

    return max(0, remaining)


def fit_chunks_to_context(chunks: List[Dict[str, Any]],
                         context_template: str,
                         query: str,
                         max_context_tokens: int = None) -> List[Dict[str, Any]]:
    """
    Select and trim chunks to fit within the context token limit.

    Args:
        chunks: List of document chunks with content
        context_template: Template for how chunks will be formatted in context
        query: User query that will be part of the prompt
        max_context_tokens: Maximum context tokens (defaults to settings.LLM_MAX_TOKENS)

    Returns:
        List of chunks that fit within the context limit
    """
    if max_context_tokens is None:
        max_context_tokens = settings.LLM_MAX_TOKENS

    # Calculate base tokens used by template and query
    base_content = context_template.format(context="", query=query)
    base_tokens = count_tokens(base_content)

    # Reserve some tokens for model response and safety margin
    reserved_tokens = 500  # Reserve tokens for model response
    available_tokens = max_context_tokens - base_tokens - reserved_tokens

    if available_tokens <= 0:
        return []

    selected_chunks = []
    used_tokens = 0

    for chunk in chunks:
        chunk_content = chunk.get('content', chunk.get('text_content', ''))
        chunk_tokens = count_tokens(chunk_content)

        if used_tokens + chunk_tokens <= available_tokens:
            selected_chunks.append(chunk)
            used_tokens += chunk_tokens
        else:
            # Try to trim the current chunk to fit
            remaining_tokens = available_tokens - used_tokens
            if remaining_tokens > 0:
                trimmed_content = truncate_text_to_tokens(chunk_content, remaining_tokens)
                if trimmed_content.strip():  # Only add if there's meaningful content
                    trimmed_chunk = chunk.copy()
                    if 'content' in trimmed_chunk:
                        trimmed_chunk['content'] = trimmed_content
                    elif 'text_content' in trimmed_chunk:
                        trimmed_chunk['text_content'] = trimmed_content
                    selected_chunks.append(trimmed_chunk)
            break  # No more space for additional chunks

    return selected_chunks


class PromptOptimizer:
    """
    Utility class for optimizing prompts to maximize context usage.
    """

    def __init__(self):
        """Initialize the prompt optimizer."""
        self.token_counter = TokenCounter()

    def optimize_context_for_max_usage(
        self,
        chunks: List[Dict[str, Any]],
        context_template: str,
        query: str,
        max_context_tokens: int
    ) -> List[Dict[str, Any]]:
        """
        Optimize context to maximize usage of available tokens.

        Args:
            chunks: List of document chunks with content
            context_template: Template for how chunks will be formatted in context
            query: User query that will be part of the prompt
            max_context_tokens: Maximum context tokens available

        Returns:
            List of chunks that optimally use the available token space
        """
        # Calculate base tokens used by template and query
        base_content = context_template.format(context="", query=query)
        base_tokens = self.token_counter.count_tokens(base_content)

        # Reserve minimal tokens for safety margin
        reserved_tokens = 100  # Minimal safety margin for optimization
        available_tokens = max_context_tokens - base_tokens - reserved_tokens

        if available_tokens <= 0:
            return []

        # Sort chunks by importance (assumed to be in order of relevance)
        # and try to include as many as possible while maximizing token usage
        selected_chunks = []
        used_tokens = 0

        for chunk in chunks:
            chunk_content = chunk.get('content', chunk.get('text_content', ''))
            chunk_tokens = self.token_counter.count_tokens(chunk_content)

            # Check if we can fit this chunk and still have room for more content
            # to maximize utilization
            if used_tokens + chunk_tokens <= available_tokens:
                selected_chunks.append(chunk)
                used_tokens += chunk_tokens
            else:
                # Check if we can trim this chunk to maximize space usage
                remaining_tokens = available_tokens - used_tokens
                if remaining_tokens > 0:
                    # Calculate how much of the current chunk we can take to maximize utilization
                    # without wasting tokens
                    optimized_chunk_content = self._optimize_chunk_trimming(
                        chunk_content,
                        remaining_tokens
                    )

                    if optimized_chunk_content.strip():
                        optimized_chunk = chunk.copy()
                        if 'content' in optimized_chunk:
                            optimized_chunk['content'] = optimized_chunk_content
                        elif 'text_content' in optimized_chunk:
                            optimized_chunk['text_content'] = optimized_chunk_content
                        selected_chunks.append(optimized_chunk)

                break  # No more space available

        return selected_chunks

    def _optimize_chunk_trimming(self, content: str, target_tokens: int) -> str:
        """
        Optimize chunk trimming to maximize information retention while hitting target token count.

        Args:
            content: The content to trim
            target_tokens: Target token count for the trimmed content

        Returns:
            Optimized trimmed content that uses tokens efficiently
        """
        # If the content already fits, return as is
        current_tokens = self.token_counter.count_tokens(content)
        if current_tokens <= target_tokens:
            return content

        # Try to intelligently trim preserving key information
        # This is a simple optimization - in practice, you might use more sophisticated methods
        optimized_content = self.token_counter.truncate_text_to_tokens(content, target_tokens)

        # Verify that the result is close to the target (within 10%)
        result_tokens = self.token_counter.count_tokens(optimized_content)
        token_utilization = result_tokens / target_tokens if target_tokens > 0 else 0

        # If utilization is poor (< 80%), consider alternative strategies
        if token_utilization < 0.8:
            # Try sentence-based trimming to preserve more coherent content
            sentences = content.split('. ')
            if len(sentences) > 1:
                selected_sentences = []
                accumulated_tokens = 0

                for sentence in sentences:
                    test_content = '. '.join(selected_sentences + [sentence]) if selected_sentences else sentence
                    test_tokens = self.token_counter.count_tokens(test_content)

                    if test_tokens <= target_tokens:
                        selected_sentences.append(sentence)
                        accumulated_tokens = test_tokens
                    else:
                        # Add what we can of the current sentence
                        remaining_tokens = target_tokens - accumulated_tokens
                        if remaining_tokens > 10:  # Worth adding partial sentence
                            partial_sentence = self.token_counter.truncate_text_to_tokens(sentence, remaining_tokens)
                            if partial_sentence.strip():
                                selected_sentences.append(partial_sentence)
                        break

                if selected_sentences:
                    optimized_content = '. '.join(selected_sentences)

        return optimized_content

    def calculate_optimal_chunk_size(
        self,
        num_chunks: int,
        context_template: str,
        query: str,
        max_context_tokens: int
    ) -> Dict[str, int]:
        """
        Calculate optimal token distribution for a given number of chunks.

        Args:
            num_chunks: Number of chunks to distribute tokens across
            context_template: Template for context formatting
            query: User query
            max_context_tokens: Maximum available tokens

        Returns:
            Dictionary with optimal token allocation
        """
        # Calculate base overhead
        base_content = context_template.format(context="", query=query)
        base_tokens = self.token_counter.count_tokens(base_content)

        # Reserve some tokens for formatting and safety margin
        reserved_tokens = 100
        available_tokens = max_context_tokens - base_tokens - reserved_tokens

        if available_tokens <= 0 or num_chunks <= 0:
            return {
                "total_available": available_tokens,
                "per_chunk_allocation": 0,
                "total_for_chunks": 0
            }

        # Calculate allocation per chunk
        per_chunk_tokens = available_tokens // num_chunks
        total_for_chunks = per_chunk_tokens * num_chunks

        return {
            "total_available": available_tokens,
            "per_chunk_allocation": per_chunk_tokens,
            "total_for_chunks": total_for_chunks,
            "remaining_tokens": available_tokens - total_for_chunks
        }

    def compress_prompt(self, prompt: str, target_tokens: int) -> str:
        """
        Compress a prompt to fit within target token count while preserving meaning.

        Args:
            prompt: The prompt to compress
            target_tokens: Target token count

        Returns:
            Compressed prompt that fits within token limits
        """
        current_tokens = self.token_counter.count_tokens(prompt)

        if current_tokens <= target_tokens:
            return prompt

        # For compression, we might try different strategies:
        # 1. Simple truncation (already implemented)
        # 2. More sophisticated compression preserving key elements

        # Try to preserve the most important parts: query and context introduction
        lines = prompt.split('\n')
        compressed_lines = []
        accumulated_tokens = 0

        for line in lines:
            test_prompt = '\n'.join(compressed_lines + [line]) if compressed_lines else line
            test_tokens = self.token_counter.count_tokens(test_prompt)

            if test_tokens <= target_tokens:
                compressed_lines.append(line)
                accumulated_tokens = test_tokens
            else:
                # Try to compress the current line
                remaining_tokens = target_tokens - accumulated_tokens
                if remaining_tokens > 20:  # Worth trying to compress
                    compressed_line = self.token_counter.truncate_text_to_tokens(line, remaining_tokens)
                    if compressed_line.strip():
                        compressed_lines.append(compressed_line)
                break

        return '\n'.join(compressed_lines)


# Global prompt optimizer instance
prompt_optimizer = PromptOptimizer()


def optimize_context_for_max_usage(
    chunks: List[Dict[str, Any]],
    context_template: str,
    query: str,
    max_context_tokens: int
) -> List[Dict[str, Any]]:
    """
    Optimize context to maximize usage of available tokens.

    Args:
        chunks: List of document chunks with content
        context_template: Template for how chunks will be formatted in context
        query: User query that will be part of the prompt
        max_context_tokens: Maximum context tokens available

    Returns:
        List of chunks that optimally use the available token space
    """
    return prompt_optimizer.optimize_context_for_max_usage(
        chunks, context_template, query, max_context_tokens
    )


def calculate_optimal_chunk_size(
    num_chunks: int,
    context_template: str,
    query: str,
    max_context_tokens: int
) -> Dict[str, int]:
    """
    Calculate optimal token distribution for a given number of chunks.

    Args:
        num_chunks: Number of chunks to distribute tokens across
        context_template: Template for context formatting
        query: User query
        max_context_tokens: Maximum available tokens

    Returns:
        Dictionary with optimal token allocation
    """
    return prompt_optimizer.calculate_optimal_chunk_size(
        num_chunks, context_template, query, max_context_tokens
    )


def compress_prompt(prompt: str, target_tokens: int) -> str:
    """
    Compress a prompt to fit within target token count while preserving meaning.

    Args:
        prompt: The prompt to compress
        target_tokens: Target token count

    Returns:
        Compressed prompt that fits within token limits
    """
    return prompt_optimizer.compress_prompt(prompt, target_tokens)


if __name__ == "__main__":
    # Example usage
    print("Token Counter initialized!")
    print(f"Sample text token count: {count_tokens('Hello, world! This is a test.')}")

    # Test truncation
    long_text = "This is a very long text that will be truncated. " * 100
    truncated = truncate_text_to_tokens(long_text, 20)
    print(f"Original tokens: {count_tokens(long_text)}")
    print(f"Truncated tokens: {count_tokens(truncated)}")
    print(f"Truncated text: {truncated[:100]}...")