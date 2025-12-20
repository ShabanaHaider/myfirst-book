"""
Text utility functions for token counting and text processing.
"""
import re
from typing import List, Tuple
import tiktoken


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Count the number of tokens in a text using tiktoken (OpenAI's tokenizer).
    This is an approximation since we're not using OpenAI models, but it's a good proxy.

    Args:
        text: The text to count tokens for
        model: The model name to use for tokenization (default: gpt-3.5-turbo)

    Returns:
        Number of tokens in the text
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback: estimate using characters (rough approximation: 4 chars per token)
        return len(text) // 4


def split_text_by_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex patterns.

    Args:
        text: The text to split into sentences

    Returns:
        List of sentences
    """
    # Pattern to match sentence endings: . ! ? followed by whitespace or end of string
    # Handles abbreviations by looking for capital letters after the period
    sentence_endings = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+'
    sentences = re.split(sentence_endings, text)
    # Remove empty strings and strip whitespace
    return [s.strip() for s in sentences if s.strip()]


def chunk_text_semantically(text: str, max_tokens: int = 512, overlap_percentage: int = 20) -> List[str]:
    """
    Split text into semantic chunks with overlap.

    Args:
        text: The text to chunk
        max_tokens: Maximum number of tokens per chunk
        overlap_percentage: Percentage of overlap between chunks

    Returns:
        List of text chunks
    """
    sentences = split_text_by_sentences(text)
    chunks = []
    current_chunk = ""
    current_token_count = 0

    # Calculate overlap in tokens
    overlap_tokens = int(max_tokens * overlap_percentage / 100)

    for sentence in sentences:
        sentence_token_count = count_tokens(sentence)

        # If adding this sentence would exceed the max token count
        if current_token_count + sentence_token_count > max_tokens:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            # Start a new chunk with potential overlap
            # Find sentences from the end of current chunk that fit within overlap limit
            if overlap_tokens > 0:
                # Add overlapping content from the end of the current chunk
                overlap_sentences = []
                overlap_count = 0

                # Work backwards to find sentences that fit within overlap limit
                temp_chunk = current_chunk
                temp_sentences = split_text_by_sentences(temp_chunk)
                for sent in reversed(temp_sentences):
                    sent_tokens = count_tokens(sent)
                    if overlap_count + sent_tokens <= overlap_tokens:
                        overlap_sentences.insert(0, sent)
                        overlap_count += sent_tokens
                    else:
                        break

                current_chunk = " ".join(overlap_sentences)
                current_token_count = overlap_count
            else:
                current_chunk = ""
                current_token_count = 0

        current_chunk += " " + sentence if current_chunk else sentence
        current_token_count += sentence_token_count

    # Add the last chunk if it's not empty
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing.

    Args:
        text: The text to clean

    Returns:
        Cleaned text
    """
    # Remove extra whitespace while preserving sentence structure
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def extract_meaningful_content(text: str, min_word_count: int = 5) -> str:
    """
    Extract meaningful content from text based on minimum word count.

    Args:
        text: The text to evaluate
        min_word_count: Minimum number of words required for content to be meaningful

    Returns:
        The text if it's meaningful, otherwise empty string
    """
    words = text.split()
    if len(words) >= min_word_count:
        return text
    return ""


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text, preserving paragraph breaks.

    Args:
        text: The text to normalize

    Returns:
        Text with normalized whitespace
    """
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    # Replace multiple newlines with max 2 newlines (preserve paragraphs)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove leading/trailing whitespace
    return text.strip()


def truncate_text_to_tokens(text: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> str:
    """
    Truncate text to fit within a maximum number of tokens.

    Args:
        text: The text to truncate
        max_tokens: Maximum number of tokens allowed
        model: The model name to use for tokenization

    Returns:
        Truncated text that fits within the token limit
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        tokens = encoding.encode(text)

        if len(tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[:max_tokens]
        return encoding.decode(truncated_tokens)
    except Exception:
        # Fallback: truncate by character count (rough approximation)
        approx_char_count = max_tokens * 4  # 4 chars per token approximation
        return text[:approx_char_count]


def remove_boilerplate_content(text: str) -> str:
    """
    Remove common boilerplate content from text (e.g., Docusaurus-specific elements).

    Args:
        text: The text to clean

    Returns:
        Text with boilerplate content removed
    """
    # Remove YAML frontmatter (common in Docusaurus)
    text = re.sub(r'^---\n.*?\n---\n?', '', text, flags=re.DOTALL)

    # Remove common navigation elements and headers/footers patterns
    # This is a simplified version - in practice, you might need more specific patterns
    boilerplate_patterns = [
        r'\{\{.*?\}\}',  # Template placeholders
        r'<\!--.*?-->',  # HTML comments
    ]

    for pattern in boilerplate_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL)

    # Clean up extra whitespace created by removals
    text = normalize_whitespace(text)

    return text