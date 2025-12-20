"""
Hash utility functions for content hashing.
"""
import hashlib
import json
from typing import Any, Union


def generate_content_hash(content: Union[str, bytes, Any]) -> str:
    """
    Generate a SHA256 hash for content.

    Args:
        content: Content to hash (string, bytes, or any JSON-serializable object)

    Returns:
        SHA256 hash of the content as a hex string
    """
    if isinstance(content, str):
        content_bytes = content.encode('utf-8')
    elif isinstance(content, bytes):
        content_bytes = content
    else:
        # For other types, serialize to JSON first
        content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        content_bytes = content_str.encode('utf-8')

    return hashlib.sha256(content_bytes).hexdigest()


def generate_text_hash(text: str) -> str:
    """
    Generate a hash specifically for text content.

    Args:
        text: Text to hash

    Returns:
        SHA256 hash of the text
    """
    return generate_content_hash(text.strip().lower())


def generate_file_hash_from_content(content: str) -> str:
    """
    Generate a hash for file content with normalization.

    Args:
        content: File content as string

    Returns:
        SHA256 hash of the normalized content
    """
    # Normalize the content before hashing
    normalized_content = content.strip()
    return generate_content_hash(normalized_content)


def generate_chunk_hash(text_content: str, source_file_path: str, chunk_index: int) -> str:
    """
    Generate a unique hash for a document chunk based on its content and metadata.

    Args:
        text_content: The text content of the chunk
        source_file_path: Path to the source file
        chunk_index: Index of the chunk in the source file

    Returns:
        SHA256 hash combining content and metadata
    """
    chunk_data = {
        'text_content': text_content.strip().lower(),
        'source_file_path': source_file_path.lower(),
        'chunk_index': chunk_index
    }
    return generate_content_hash(chunk_data)


def generate_embedding_hash(vector: list, source_file_path: str, chunk_index: int) -> str:
    """
    Generate a hash for an embedding based on vector and metadata.

    Args:
        vector: The embedding vector
        source_file_path: Path to the source file
        chunk_index: Index of the chunk in the source file

    Returns:
        SHA256 hash combining vector and metadata
    """
    embedding_data = {
        'vector_hash': generate_content_hash(str(vector)),
        'source_file_path': source_file_path.lower(),
        'chunk_index': chunk_index
    }
    return generate_content_hash(embedding_data)


def compare_hashes(hash1: str, hash2: str) -> bool:
    """
    Compare two hashes for equality.

    Args:
        hash1: First hash to compare
        hash2: Second hash to compare

    Returns:
        True if hashes are identical, False otherwise
    """
    return hash1 == hash2


def generate_metadata_hash(metadata: dict) -> str:
    """
    Generate a hash for metadata dictionary.

    Args:
        metadata: Metadata dictionary to hash

    Returns:
        SHA256 hash of the metadata
    """
    return generate_content_hash(metadata)


def generate_document_hash(document_content: str, metadata: dict = None) -> str:
    """
    Generate a hash for a complete document including its content and metadata.

    Args:
        document_content: The content of the document
        metadata: Optional metadata dictionary

    Returns:
        SHA256 hash of the document content and metadata
    """
    if metadata:
        doc_data = {
            'content': document_content.strip().lower(),
            'metadata': metadata
        }
    else:
        doc_data = document_content.strip().lower()

    return generate_content_hash(doc_data)