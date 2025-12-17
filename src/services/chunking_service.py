"""
Chunking service for semantic, token-limited chunking.
"""
from typing import List, Dict, Any, Tuple
from src.utils.text_utils import chunk_text_semantically, count_tokens, extract_meaningful_content
from src.utils.hash_utils import generate_chunk_hash
from src.utils.logging import StructuredLogger, log_ingestion_event
from src.models.document_chunk import DocumentChunk
from src.exceptions import ValidationError
import uuid
from datetime import datetime


class ChunkingService:
    """
    Service for splitting text into semantic, token-limited chunks.
    """

    def __init__(self):
        """Initialize the chunking service."""
        self.logger = StructuredLogger("chunking_service")

    def create_chunks(
        self,
        text: str,
        source_file_path: str,
        max_tokens: int = 512,
        overlap_percentage: int = 20,
        min_word_count: int = 5
    ) -> List[DocumentChunk]:
        """
        Create chunks from text with semantic splitting and token limits.

        Args:
            text: The text to chunk
            source_file_path: Path to the source file
            max_tokens: Maximum number of tokens per chunk
            overlap_percentage: Percentage of overlap between chunks
            min_word_count: Minimum number of words for meaningful content

        Returns:
            List of DocumentChunk objects
        """
        try:
            # Split text into semantic chunks
            text_chunks = chunk_text_semantically(
                text=text,
                max_tokens=max_tokens,
                overlap_percentage=overlap_percentage
            )

            # Create DocumentChunk objects
            document_chunks = []
            for i, chunk_text in enumerate(text_chunks):
                # Validate chunk quality
                meaningful_content = extract_meaningful_content(chunk_text, min_word_count)
                if not meaningful_content:
                    self.logger.warning(
                        "Skipping low-quality chunk",
                        source_file_path=source_file_path,
                        chunk_index=i,
                        reason="insufficient meaningful content"
                    )
                    continue

                # Generate a unique ID for the chunk
                chunk_id = str(uuid.uuid4())

                # Generate content hash
                content_hash = generate_chunk_hash(chunk_text, source_file_path, i)

                # Create DocumentChunk object
                chunk = DocumentChunk(
                    id=chunk_id,
                    text_content=meaningful_content,
                    source_file_path=source_file_path,
                    chunk_index=i,
                    character_position=text.find(chunk_text),  # Approximate position
                    content_hash=content_hash,
                    created_at=datetime.now()
                )

                document_chunks.append(chunk)

            log_ingestion_event(
                event="chunking_success",
                file_path=source_file_path,
                status="success",
                chunks_created=len(document_chunks),
                max_tokens=max_tokens,
                overlap_percentage=overlap_percentage
            )

            return document_chunks

        except Exception as e:
            self.logger.error("Failed to create chunks", source_file_path=source_file_path, error=str(e))
            log_ingestion_event(
                event="chunking_failed",
                file_path=source_file_path,
                status="error",
                error=str(e)
            )
            raise ValidationError(f"Failed to chunk text from {source_file_path}: {str(e)}")

    def validate_chunk(self, chunk: DocumentChunk, max_tokens: int = 512, min_word_count: int = 5) -> Tuple[bool, List[str]]:
        """
        Validate a document chunk.

        Args:
            chunk: The DocumentChunk to validate
            max_tokens: Maximum allowed tokens
            min_word_count: Minimum word count for meaningful content

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check token count
        token_count = count_tokens(chunk.text_content)
        if token_count > max_tokens:
            issues.append(f"Chunk has {token_count} tokens, exceeding limit of {max_tokens}")

        # Check word count
        word_count = len(chunk.text_content.split())
        if word_count < min_word_count:
            issues.append(f"Chunk has {word_count} words, below minimum of {min_word_count}")

        # Check for empty content
        if not chunk.text_content.strip():
            issues.append("Chunk content is empty")

        # Check required fields
        if not chunk.id:
            issues.append("Chunk ID is missing")

        if not chunk.source_file_path:
            issues.append("Source file path is missing")

        if chunk.chunk_index < 0:
            issues.append("Chunk index is negative")

        is_valid = len(issues) == 0
        return is_valid, issues

    def validate_chunks(self, chunks: List[DocumentChunk], max_tokens: int = 512, min_word_count: int = 5) -> Dict[str, Any]:
        """
        Validate a list of document chunks.

        Args:
            chunks: List of DocumentChunk objects to validate
            max_tokens: Maximum allowed tokens
            min_word_count: Minimum word count for meaningful content

        Returns:
            Dictionary with validation results
        """
        results = {
            "total_chunks": len(chunks),
            "valid_chunks": 0,
            "invalid_chunks": 0,
            "issues": [],
            "validation_details": []
        }

        for i, chunk in enumerate(chunks):
            is_valid, issues = self.validate_chunk(chunk, max_tokens, min_word_count)

            validation_detail = {
                "chunk_index": i,
                "chunk_id": chunk.id,
                "is_valid": is_valid,
                "issues": issues
            }

            if is_valid:
                results["valid_chunks"] += 1
            else:
                results["invalid_chunks"] += 1
                results["issues"].extend(issues)

            results["validation_details"].append(validation_detail)

        return results

    def merge_small_chunks(self, chunks: List[DocumentChunk], min_token_threshold: int = 100) -> List[DocumentChunk]:
        """
        Merge small chunks with adjacent chunks if they're below the threshold.

        Args:
            chunks: List of DocumentChunk objects
            min_token_threshold: Minimum token count threshold

        Returns:
            List of merged DocumentChunk objects
        """
        if not chunks:
            return chunks

        merged_chunks = []
        i = 0

        while i < len(chunks):
            current_chunk = chunks[i]
            current_tokens = count_tokens(current_chunk.text_content)

            # If current chunk is above threshold, add it as is
            if current_tokens >= min_token_threshold:
                merged_chunks.append(current_chunk)
                i += 1
            else:
                # If below threshold, try to merge with next chunk
                if i + 1 < len(chunks):
                    next_chunk = chunks[i + 1]
                    merged_text = current_chunk.text_content + " " + next_chunk.text_content

                    # Check if merged content is still within token limit
                    merged_tokens = count_tokens(merged_text)
                    if merged_tokens <= 512:  # Default max tokens
                        # Create a new merged chunk
                        merged_chunk = DocumentChunk(
                            id=str(uuid.uuid4()),
                            text_content=merged_text,
                            source_file_path=current_chunk.source_file_path,
                            chunk_index=current_chunk.chunk_index,
                            character_position=current_chunk.character_position,
                            content_hash=generate_chunk_hash(merged_text, current_chunk.source_file_path, current_chunk.chunk_index),
                            created_at=datetime.now()
                        )
                        merged_chunks.append(merged_chunk)
                        i += 2  # Skip both original chunks
                    else:
                        # If merging would exceed limit, keep both chunks
                        merged_chunks.append(current_chunk)
                        i += 1
                else:
                    # Last chunk, add it as is
                    merged_chunks.append(current_chunk)
                    i += 1

        return merged_chunks

    def split_large_chunk(self, chunk: DocumentChunk, max_tokens: int = 512) -> List[DocumentChunk]:
        """
        Split a large chunk into smaller chunks.

        Args:
            chunk: The DocumentChunk to split
            max_tokens: Maximum tokens per split chunk

        Returns:
            List of smaller DocumentChunk objects
        """
        # Split the chunk's text content
        text_chunks = chunk_text_semantically(
            text=chunk.text_content,
            max_tokens=max_tokens,
            overlap_percentage=20
        )

        result_chunks = []
        for i, text_chunk in enumerate(text_chunks):
            new_chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                text_content=text_chunk,
                source_file_path=chunk.source_file_path,
                chunk_index=chunk.chunk_index + i,  # Adjust index based on split position
                character_position=chunk.character_position + chunk.text_content.find(text_chunk),
                content_hash=generate_chunk_hash(text_chunk, chunk.source_file_path, chunk.chunk_index + i),
                created_at=datetime.now()
            )
            result_chunks.append(new_chunk)

        return result_chunks

    def rechunk_document(self, chunks: List[DocumentChunk], max_tokens: int = 512) -> List[DocumentChunk]:
        """
        Rechunk a list of chunks to ensure they all meet size requirements.

        Args:
            chunks: List of DocumentChunk objects
            max_tokens: Maximum tokens per chunk

        Returns:
            List of properly sized DocumentChunk objects
        """
        rechunked = []

        for chunk in chunks:
            token_count = count_tokens(chunk.text_content)

            if token_count > max_tokens:
                # Split large chunk
                split_chunks = self.split_large_chunk(chunk, max_tokens)
                rechunked.extend(split_chunks)
            else:
                # Add appropriately sized chunk
                rechunked.append(chunk)

        return rechunked

    def get_chunk_statistics(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        Get statistics about a list of chunks.

        Args:
            chunks: List of DocumentChunk objects

        Returns:
            Dictionary with chunk statistics
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "total_tokens": 0,
                "avg_tokens_per_chunk": 0,
                "min_tokens": 0,
                "max_tokens": 0,
                "avg_word_count": 0
            }

        token_counts = []
        word_counts = []

        for chunk in chunks:
            token_count = count_tokens(chunk.text_content)
            word_count = len(chunk.text_content.split())

            token_counts.append(token_count)
            word_counts.append(word_count)

        return {
            "total_chunks": len(chunks),
            "total_tokens": sum(token_counts),
            "avg_tokens_per_chunk": sum(token_counts) / len(token_counts),
            "min_tokens": min(token_counts),
            "max_tokens": max(token_counts),
            "avg_word_count": sum(word_counts) / len(word_counts),
            "total_characters": sum(len(chunk.text_content) for chunk in chunks)
        }

    def create_chunks_from_file_content(
        self,
        file_path: str,
        file_content: str,
        max_tokens: int = 512,
        overlap_percentage: int = 20,
        min_word_count: int = 5
    ) -> List[DocumentChunk]:
        """
        Create chunks directly from file content.

        Args:
            file_path: Path to the source file
            file_content: Content of the file
            max_tokens: Maximum tokens per chunk
            overlap_percentage: Overlap percentage between chunks
            min_word_count: Minimum word count for meaningful content

        Returns:
            List of DocumentChunk objects
        """
        return self.create_chunks(
            text=file_content,
            source_file_path=file_path,
            max_tokens=max_tokens,
            overlap_percentage=overlap_percentage,
            min_word_count=min_word_count
        )

    def remove_duplicate_chunks(self, chunks: List[DocumentChunk], similarity_threshold: float = 0.9) -> List[DocumentChunk]:
        """
        Remove duplicate chunks based on content similarity.

        Args:
            chunks: List of DocumentChunk objects
            similarity_threshold: Threshold for considering chunks as duplicates (0.0-1.0)

        Returns:
            List of unique DocumentChunk objects
        """
        if not chunks:
            return chunks

        unique_chunks = []
        seen_content_hashes = set()

        for chunk in chunks:
            # Use the content hash for exact duplicates
            if chunk.content_hash not in seen_content_hashes:
                seen_content_hashes.add(chunk.content_hash)
                unique_chunks.append(chunk)

        return unique_chunks

    def health_check(self) -> bool:
        """
        Check if the chunking service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Test with a simple text
            test_text = "This is a test sentence. " * 20  # Should create multiple chunks
            chunks = self.create_chunks(test_text, "test.md", max_tokens=50)
            return len(chunks) > 0
        except Exception:
            return False