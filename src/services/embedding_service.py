"""
Embedding service for async batch processing with Cohere API.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from src.clients.cohere_client import CohereWrapper
from src.clients.qdrant_client import QdrantWrapper
from src.models.embedding_vector import EmbeddingVector
from src.models.document_chunk import DocumentChunk
from src.utils.hash_utils import generate_content_hash
from src.utils.async_utils import async_retry_with_backoff
import time


class EmbeddingService:
    """
    Service for generating embeddings with async batch processing and error handling.
    """

    def __init__(self):
        """Initialize the embedding service with required clients."""
        self.cohere_client = CohereWrapper()
        self.qdrant_client = QdrantWrapper()
        self.batch_size = self.cohere_client.batch_size
        self.max_concurrent_requests = 5  # Limit concurrent requests to be respectful to API

    async def generate_embeddings_for_chunks(self, chunks: List[DocumentChunk]) -> List[EmbeddingVector]:
        """
        Generate embeddings for a list of document chunks asynchronously.

        Args:
            chunks: List of DocumentChunk objects to embed

        Returns:
            List of EmbeddingVector objects with generated embeddings
        """
        logging.info(f"Generating embeddings for {len(chunks)} chunks")

        # Prepare texts for embedding
        texts = [chunk.text_content for chunk in chunks]

        # Generate embeddings in batches
        embeddings = await self._generate_embeddings_batch(texts)

        # Validate embeddings
        if not self.cohere_client.validate_embeddings(embeddings):
            raise ValueError("Generated embeddings failed validation")

        # Create EmbeddingVector objects
        embedding_vectors = []
        for i, chunk in enumerate(chunks):
            embedding_vector = EmbeddingVector(
                id=chunk.id,
                vector=embeddings[i],
                metadata={
                    "source_file_path": chunk.source_file_path,
                    "chunk_index": chunk.chunk_index,
                    "character_position": chunk.character_position,
                    "content_hash": chunk.content_hash,
                    "original_content_length": len(chunk.text_content)
                },
                collection_name=self.qdrant_client.collection_name,
                created_at=chunk.created_at
            )
            embedding_vectors.append(embedding_vector)

        logging.info(f"Successfully generated {len(embedding_vectors)} embedding vectors")
        return embedding_vectors

    async def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using async batch processing with retry logic.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        # Process in batches to respect API limits and implement retry logic
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            # Add some delay between batches to be respectful to the API
            if i > 0:
                await asyncio.sleep(0.1)

            # Generate embeddings for the batch with retry logic
            batch_embeddings = await self._generate_embeddings_with_retry(batch)
            all_embeddings.extend(batch_embeddings)

            logging.info(f"Processed batch {i//self.batch_size + 1}/{(len(texts)-1)//self.batch_size + 1}")

        return all_embeddings

    async def _generate_embeddings_with_retry(self, batch: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch with retry logic and error handling.

        Args:
            batch: Batch of text strings to embed

        Returns:
            List of embedding vectors for the batch
        """
        async def _embed_batch():
            return await self.cohere_client.embed_text_async(batch, input_type="search_document")

        try:
            # Use retry with backoff for API resilience
            result = await async_retry_with_backoff(
                _embed_batch,
                max_retries=3,
                base_delay=1.0,
                max_delay=10.0
            )
            return result
        except Exception as e:
            logging.error(f"Failed to generate embeddings for batch after retries: {e}")
            raise

    async def store_embeddings(self, embedding_vectors: List[EmbeddingVector]) -> bool:
        """
        Store embedding vectors in Qdrant with error handling.

        Args:
            embedding_vectors: List of EmbeddingVector objects to store

        Returns:
            True if successful
        """
        if not embedding_vectors:
            logging.warning("No embeddings to store")
            return True

        try:
            # Store embeddings in batches to optimize performance
            success = self.qdrant_client.upsert_embeddings_batch(embedding_vectors)

            if success:
                logging.info(f"Successfully stored {len(embedding_vectors)} embeddings in Qdrant")
            else:
                logging.error(f"Failed to store {len(embedding_vectors)} embeddings in Qdrant")

            return success
        except Exception as e:
            logging.error(f"Error storing embeddings in Qdrant: {e}")
            return False

    async def process_and_store_chunks(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        Complete workflow: generate embeddings for chunks and store in Qdrant.

        Args:
            chunks: List of DocumentChunk objects to process

        Returns:
            Dictionary with processing results and statistics
        """
        start_time = time.time()

        try:
            # Generate embeddings
            embedding_vectors = await self.generate_embeddings_for_chunks(chunks)

            # Store embeddings in Qdrant
            store_success = await self.store_embeddings(embedding_vectors)

            processing_time = time.time() - start_time

            result = {
                "success": store_success,
                "chunks_processed": len(chunks),
                "embeddings_generated": len(embedding_vectors),
                "processing_time_seconds": processing_time,
                "qdrant_collection": self.qdrant_client.collection_name
            }

            if store_success:
                logging.info(f"Successfully processed and stored {len(chunks)} chunks")
            else:
                logging.error("Failed to store embeddings in Qdrant")

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logging.error(f"Error in complete processing workflow: {e}")

            return {
                "success": False,
                "chunks_processed": len(chunks),
                "error": str(e),
                "processing_time_seconds": processing_time
            }

    async def generate_single_embedding(self, text: str, input_type: str = "search_document") -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            input_type: Type of input (search_document, search_query, etc.)

        Returns:
            Embedding vector
        """
        try:
            embedding = await self.cohere_client.embed_text_async(text, input_type)
            return embedding[0]  # Return the first (and only) embedding
        except Exception as e:
            logging.error(f"Failed to generate single embedding: {e}")
            raise

    def validate_embedding_dimensions(self, embeddings: List[List[float]]) -> bool:
        """
        Validate that all embeddings have the correct dimensions.

        Args:
            embeddings: List of embedding vectors to validate

        Returns:
            True if all embeddings have correct dimensions
        """
        return self.cohere_client.validate_embeddings(embeddings)