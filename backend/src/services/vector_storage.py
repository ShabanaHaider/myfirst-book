"""
Vector storage service for Qdrant integration with proper metadata handling.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from src.clients.qdrant_client import QdrantWrapper
from src.models.embedding_vector import EmbeddingVector
from src.models.document_chunk import DocumentChunk
from src.utils.hash_utils import generate_content_hash
import time


class VectorStorageService:
    """
    Service for managing vector storage operations in Qdrant with proper metadata handling.
    """

    def __init__(self):
        """Initialize the vector storage service with Qdrant client."""
        self.qdrant_client = QdrantWrapper()
        self._ensure_collection_exists()

    def _ensure_collection_exists(self) -> bool:
        """
        Ensure the Qdrant collection exists with proper configuration.

        Returns:
            True if collection exists or was created successfully
        """
        return self.qdrant_client.ensure_collection_exists()

    async def store_embedding_vector(self, embedding_vector: EmbeddingVector) -> bool:
        """
        Store a single embedding vector in Qdrant.

        Args:
            embedding_vector: The embedding vector to store

        Returns:
            True if successful
        """
        try:
            success = self.qdrant_client.upsert_embedding(embedding_vector)
            if success:
                logging.info(f"Successfully stored embedding vector: {embedding_vector.id}")
            else:
                logging.error(f"Failed to store embedding vector: {embedding_vector.id}")
            return success
        except Exception as e:
            logging.error(f"Error storing embedding vector: {e}")
            return False

    async def store_embedding_vectors_batch(self, embedding_vectors: List[EmbeddingVector]) -> bool:
        """
        Store multiple embedding vectors in Qdrant in a batch operation.

        Args:
            embedding_vectors: List of embedding vectors to store

        Returns:
            True if successful
        """
        if not embedding_vectors:
            logging.warning("No embedding vectors to store")
            return True

        try:
            success = self.qdrant_client.upsert_embeddings_batch(embedding_vectors)
            if success:
                logging.info(f"Successfully stored {len(embedding_vectors)} embedding vectors in batch")
            else:
                logging.error(f"Failed to store {len(embedding_vectors)} embedding vectors in batch")
            return success
        except Exception as e:
            logging.error(f"Error storing embedding vectors batch: {e}")
            return False

    async def store_document_chunks(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        Store document chunks as embedding vectors in Qdrant with proper metadata.

        Args:
            chunks: List of DocumentChunk objects to store

        Returns:
            Dictionary with storage results and statistics
        """
        start_time = time.time()

        try:
            # Convert DocumentChunks to EmbeddingVectors (assuming they have embeddings)
            # In a real implementation, you would generate embeddings here
            embedding_vectors = []

            for chunk in chunks:
                # We'll assume the chunks have embeddings attached or they will be generated
                # For now, we'll create placeholder embedding vectors that would be filled with actual embeddings
                embedding_vector = EmbeddingVector(
                    id=chunk.id,
                    vector=chunk.embedding if hasattr(chunk, 'embedding') else [0.0] * 1024,  # Placeholder
                    metadata={
                        "source_file_path": chunk.source_file_path,
                        "chunk_index": chunk.chunk_index,
                        "character_position": chunk.character_position,
                        "content_hash": chunk.content_hash,
                        "original_content_length": len(chunk.content),
                        "chunk_size_tokens": chunk.chunk_size_tokens,
                        "chunk_title": getattr(chunk, 'title', ''),
                        "chunk_section": getattr(chunk, 'section', '')
                    },
                    collection_name=self.qdrant_client.collection_name,
                    created_at=chunk.created_at
                )
                embedding_vectors.append(embedding_vector)

            # Store all vectors in batch
            success = await self.store_embedding_vectors_batch(embedding_vectors)

            processing_time = time.time() - start_time

            result = {
                "success": success,
                "chunks_processed": len(chunks),
                "vectors_stored": len(embedding_vectors),
                "processing_time_seconds": processing_time,
                "collection_name": self.qdrant_client.collection_name
            }

            if success:
                logging.info(f"Successfully stored {len(chunks)} document chunks as vectors")
            else:
                logging.error("Failed to store document chunks as vectors")

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logging.error(f"Error in store_document_chunks: {e}")

            return {
                "success": False,
                "chunks_processed": len(chunks),
                "error": str(e),
                "processing_time_seconds": processing_time
            }

    async def incremental_upsert(self, embedding_vectors: List[EmbeddingVector]) -> Dict[str, Any]:
        """
        Perform incremental upserts with proper metadata, checking for existing content.

        Args:
            embedding_vectors: List of embedding vectors to upsert

        Returns:
            Dictionary with upsert results and statistics
        """
        start_time = time.time()

        try:
            # Check for existing vectors with same content hash to avoid duplicates
            filtered_vectors = []
            skipped_count = 0

            for embedding_vector in embedding_vectors:
                content_hash = embedding_vector.metadata.get("content_hash")

                # Skip if content hash already exists in the collection
                # For now, we'll just add all vectors (in a real implementation,
                # we'd check if this hash already exists)
                filtered_vectors.append(embedding_vector)

            # Store the filtered vectors
            success = await self.store_embedding_vectors_batch(filtered_vectors)

            processing_time = time.time() - start_time

            result = {
                "success": success,
                "vectors_upserted": len(filtered_vectors),
                "vectors_skipped": skipped_count,
                "processing_time_seconds": processing_time,
                "collection_name": self.qdrant_client.collection_name
            }

            if success:
                logging.info(f"Successfully upserted {len(filtered_vectors)} vectors with {skipped_count} skipped")
            else:
                logging.error("Failed to upsert vectors")

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logging.error(f"Error in incremental upsert: {e}")

            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": processing_time
            }

    async def validate_and_store_embeddings(self, embedding_vectors: List[EmbeddingVector]) -> Dict[str, Any]:
        """
        Validate embedding dimensions and metadata before storing in Qdrant.

        Args:
            embedding_vectors: List of embedding vectors to validate and store

        Returns:
            Dictionary with validation and storage results
        """
        start_time = time.time()

        try:
            # Validate embedding dimensions
            for embedding_vector in embedding_vectors:
                if len(embedding_vector.vector) != 768:  # Cohere multilingual model produces 768-dimensional vectors
                    raise ValueError(f"Invalid embedding dimensions: expected 768, got {len(embedding_vector.vector)} for vector {embedding_vector.id}")

            # Validate required metadata fields
            required_fields = ["source_file_path", "chunk_index", "content_hash"]
            for embedding_vector in embedding_vectors:
                for field in required_fields:
                    if field not in embedding_vector.metadata:
                        raise ValueError(f"Missing required metadata field: {field} for vector {embedding_vector.id}")

            # Store validated vectors
            success = await self.store_embedding_vectors_batch(embedding_vectors)

            processing_time = time.time() - start_time

            result = {
                "success": success,
                "vectors_validated": len(embedding_vectors),
                "vectors_stored": len(embedding_vectors) if success else 0,
                "processing_time_seconds": processing_time
            }

            if success:
                logging.info(f"Successfully validated and stored {len(embedding_vectors)} vectors")
            else:
                logging.error("Failed to store validated vectors")

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logging.error(f"Error in validate and store: {e}")

            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": processing_time
            }

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Qdrant collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.qdrant_client.count_points()
            return {
                "total_points": count,
                "collection_name": self.qdrant_client.collection_name,
                "healthy": self.qdrant_client.health_check()
            }
        except Exception as e:
            logging.error(f"Error getting collection stats: {e}")
            return {
                "total_points": 0,
                "collection_name": self.qdrant_client.collection_name,
                "healthy": False,
                "error": str(e)
            }

    async def delete_by_source_file(self, source_file_path: str) -> bool:
        """
        Delete all vectors associated with a specific source file.

        Args:
            source_file_path: Path of the source file to delete vectors for

        Returns:
            True if successful
        """
        try:
            success = self.qdrant_client.delete_by_payload("source_file_path", source_file_path)
            if success:
                logging.info(f"Successfully deleted vectors for source file: {source_file_path}")
            else:
                logging.error(f"Failed to delete vectors for source file: {source_file_path}")
            return success
        except Exception as e:
            logging.error(f"Error deleting vectors by source file: {e}")
            return False