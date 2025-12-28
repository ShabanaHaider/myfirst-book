"""
Cohere client wrapper with API key management.
"""
import asyncio
import logging
from typing import List, Union
import cohere
from src.config.settings import settings
from src.utils.async_utils import async_retry_with_backoff


class CohereWrapper:
    """
    A wrapper around the Cohere client with API key management and async support.
    """

    def __init__(self):
        """Initialize the Cohere client with API key."""
        if not settings.COHERE_API_KEY:
            raise ValueError("COHERE_API_KEY is required")

        self.client = cohere.Client(settings.COHERE_API_KEY)
        self.model = "embed-multilingual-v2.0"  # Cohere multilingual embedding model
        self.batch_size = settings.BATCH_SIZE

    def embed_text(self, texts: Union[str, List[str]],
                   input_type: str = "search_document") -> List[List[float]]:
        """
        Generate embeddings for text(s) synchronously.

        Args:
            texts: Single text string or list of text strings to embed
            input_type: Type of input (search_document, search_query, classification, etc.)

        Returns:
            List of embedding vectors
        """
        try:
            if isinstance(texts, str):
                texts = [texts]

            response = self.client.embed(
                texts=texts,
                model=self.model,
                input_type=input_type
            )

            return response.embeddings
        except Exception as e:
            logging.error(f"Failed to generate embeddings: {e}")
            raise

    async def embed_text_async(self, texts: Union[str, List[str]],
                              input_type: str = "search_document") -> List[List[float]]:
        """
        Generate embeddings for text(s) asynchronously with retry logic.

        Args:
            texts: Single text string or list of text strings to embed
            input_type: Type of input (search_document, search_query, classification, etc.)

        Returns:
            List of embedding vectors
        """
        async def _embed_with_retry():
            return self.embed_text(texts, input_type)

        try:
            # Use retry with backoff for API resilience
            result = await async_retry_with_backoff(
                _embed_with_retry,
                max_retries=3,
                base_delay=1.0
            )
            return result
        except Exception as e:
            logging.error(f"Failed to generate embeddings asynchronously: {e}")
            raise

    async def embed_text_batch_async(self, texts: List[str],
                                   input_type: str = "search_document") -> List[List[float]]:
        """
        Generate embeddings for a list of texts in batches asynchronously.

        Args:
            texts: List of text strings to embed
            input_type: Type of input (search_document, search_query, classification, etc.)

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        # Process in batches to respect API limits
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = await self.embed_text_async(batch, input_type)
            all_embeddings.extend(batch_embeddings)

            # Small delay between batches to be respectful to the API
            await asyncio.sleep(0.1)

        return all_embeddings

    def get_model_info(self) -> dict:
        """
        Get information about the embedding model being used.

        Returns:
            Dictionary with model information
        """
        try:
            # This is a simplified approach - Cohere doesn't have a direct model info endpoint
            # but we can return known information about the multilingual model
            return {
                "model": self.model,
                "dimensions": 768,  # Cohere multilingual model produces 768-dimensional vectors
                "max_tokens": 512,   # Maximum tokens per input
                "supported_languages": "Multiple languages"
            }
        except Exception as e:
            logging.error(f"Failed to get model info: {e}")
            return {}

    def validate_embeddings(self, embeddings: List[List[float]]) -> bool:
        """
        Validate that embeddings have the correct dimensions.

        Args:
            embeddings: List of embedding vectors to validate

        Returns:
            True if all embeddings have correct dimensions
        """
        expected_dimensions = 768  # Cohere multilingual model produces 768-dimensional vectors

        for embedding in embeddings:
            if len(embedding) != expected_dimensions:
                logging.error(f"Invalid embedding dimensions: expected {expected_dimensions}, got {len(embedding)}")
                return False

        return True

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query specifically.

        Args:
            query: Query text to embed

        Returns:
            Embedding vector for the query
        """
        embeddings = await self.embed_text_async(query, input_type="search_query")
        return embeddings[0]  # Return the first (and only) embedding

    async def embed_document(self, document: str) -> List[float]:
        """
        Generate embedding for a document specifically.

        Args:
            document: Document text to embed

        Returns:
            Embedding vector for the document
        """
        embeddings = await self.embed_text_async(document, input_type="search_document")
        return embeddings[0]  # Return the first (and only) embedding