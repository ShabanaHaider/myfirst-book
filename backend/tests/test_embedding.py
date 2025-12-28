"""
Unit tests for embedding functionality.
"""
import asyncio
import pytest
import unittest
from unittest.mock import Mock, AsyncMock, patch
from src.services.embedding_service import EmbeddingService
from src.models.document_chunk import DocumentChunk
from src.models.embedding_vector import EmbeddingVector
from datetime import datetime
from typing import List


class TestEmbeddingService(unittest.TestCase):
    """Unit tests for the EmbeddingService class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        with patch('src.services.embedding_service.CohereWrapper') as mock_cohere, \
             patch('src.services.embedding_service.QdrantWrapper') as mock_qdrant:

            # Mock the Cohere client
            self.mock_cohere_client = Mock()
            self.mock_cohere_client.batch_size = 32
            self.mock_cohere_client.validate_embeddings.return_value = True
            self.mock_cohere_client.embed_text_async = AsyncMock()
            self.mock_cohere_client.embed_text_async.return_value = [[0.1, 0.2, 0.3] + [0.0] * 1021]  # 1024-dim vector

            # Mock the Qdrant client
            self.mock_qdrant_client = Mock()
            self.mock_qdrant_client.collection_name = "test_collection"
            self.mock_qdrant_client.upsert_embeddings_batch.return_value = True

            # Patch the constructors
            mock_cohere.return_value = self.mock_cohere_client
            mock_qdrant.return_value = self.mock_qdrant_client

            self.embedding_service = EmbeddingService()

    @pytest.mark.asyncio
    async def test_generate_embeddings_for_chunks(self):
        """Test generating embeddings for document chunks."""
        # Create test chunks
        chunks = [
            DocumentChunk(
                id="chunk1",
                content="This is test content for embedding.",
                source_file_path="test.md",
                chunk_index=0,
                character_position=0,
                content_hash="hash1",
                chunk_size_tokens=100,
                created_at=datetime.now()
            )
        ]

        # Mock the Cohere client to return test embeddings
        test_embeddings = [[0.1, 0.2, 0.3] + [0.0] * 1021]  # 1024-dim vector
        self.mock_cohere_client.embed_text_async.return_value = test_embeddings

        # Call the method
        result = await self.embedding_service.generate_embeddings_for_chunks(chunks)

        # Assertions
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], EmbeddingVector)
        self.assertEqual(result[0].id, "chunk1")
        self.assertEqual(len(result[0].vector), 1024)  # Cohere vectors are 1024-dimensional
        self.assertEqual(result[0].metadata["source_file_path"], "test.md")

    @pytest.mark.asyncio
    async def test_generate_embeddings_for_chunks_validation_failure(self):
        """Test that validation failure raises an error."""
        # Create test chunks
        chunks = [
            DocumentChunk(
                id="chunk1",
                content="This is test content for embedding.",
                source_file_path="test.md",
                chunk_index=0,
                character_position=0,
                content_hash="hash1",
                chunk_size_tokens=100,
                created_at=datetime.now()
            )
        ]

        # Mock validation to fail
        self.mock_cohere_client.validate_embeddings.return_value = False

        # Expect an error
        with self.assertRaises(ValueError):
            await self.embedding_service.generate_embeddings_for_chunks(chunks)

    @pytest.mark.asyncio
    async def test_store_embeddings_success(self):
        """Test storing embeddings successfully."""
        # Create test embedding vectors
        embedding_vectors = [
            EmbeddingVector(
                id="vector1",
                vector=[0.1, 0.2, 0.3] + [0.0] * 1021,  # 1024-dim vector
                metadata={"source_file_path": "test.md", "chunk_index": 0, "content_hash": "hash1"},
                collection_name="test_collection",
                created_at=datetime.now()
            )
        ]

        # Call the method
        result = await self.embedding_service.store_embeddings(embedding_vectors)

        # Assertions
        self.assertTrue(result)
        self.mock_qdrant_client.upsert_embeddings_batch.assert_called_once_with(embedding_vectors)

    @pytest.mark.asyncio
    async def test_store_embeddings_empty_list(self):
        """Test storing an empty list of embeddings."""
        result = await self.embedding_service.store_embeddings([])
        self.assertTrue(result)  # Should return True for empty list

    @pytest.mark.asyncio
    async def test_process_and_store_chunks_success(self):
        """Test the complete workflow of processing and storing chunks."""
        # Create test chunks
        chunks = [
            DocumentChunk(
                id="chunk1",
                content="This is test content for embedding.",
                source_file_path="test.md",
                chunk_index=0,
                character_position=0,
                content_hash="hash1",
                chunk_size_tokens=100,
                created_at=datetime.now()
            )
        ]

        # Mock the Cohere client to return test embeddings
        test_embeddings = [[0.1, 0.2, 0.3] + [0.0] * 1021]  # 1024-dim vector
        self.mock_cohere_client.embed_text_async.return_value = test_embeddings

        # Call the method
        result = await self.embedding_service.process_and_store_chunks(chunks)

        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_processed"], 1)
        self.assertEqual(result["embeddings_generated"], 1)

    @pytest.mark.asyncio
    async def test_generate_single_embedding(self):
        """Test generating a single embedding."""
        test_text = "This is a test sentence."
        test_embedding = [0.1, 0.2, 0.3] + [0.0] * 1021  # 1024-dim vector
        self.mock_cohere_client.embed_text_async.return_value = [test_embedding]

        result = await self.embedding_service.generate_single_embedding(test_text)

        self.assertEqual(result, test_embedding)
        self.mock_cohere_client.embed_text_async.assert_called_once_with(test_text, "search_document")

    def test_validate_embedding_dimensions(self):
        """Test validating embedding dimensions."""
        test_embeddings = [
            [0.1, 0.2, 0.3] + [0.0] * 1021,  # 1024-dim vector
            [0.4, 0.5, 0.6] + [0.0] * 1021   # 1024-dim vector
        ]

        result = self.embedding_service.validate_embedding_dimensions(test_embeddings)
        self.assertTrue(result)

    def test_validate_embedding_dimensions_invalid(self):
        """Test validating embedding dimensions with invalid vectors."""
        test_embeddings = [
            [0.1, 0.2, 0.3, 0.4]  # Only 4 dimensions instead of 1024
        ]

        result = self.embedding_service.validate_embedding_dimensions(test_embeddings)
        self.assertFalse(result)


class TestIntegration(unittest.TestCase):
    """Integration tests for embedding functionality."""

    @pytest.mark.asyncio
    @patch('src.services.embedding_service.CohereWrapper')
    @patch('src.services.embedding_service.QdrantWrapper')
    async def test_full_embedding_process(self, mock_qdrant, mock_cohere):
        """Test the full embedding process from chunks to storage."""
        # Setup mocks
        mock_cohere_instance = Mock()
        mock_cohere_instance.batch_size = 32
        mock_cohere_instance.validate_embeddings.return_value = True
        test_embeddings = [[0.1, 0.2, 0.3] + [0.0] * 1021]  # 1024-dim vector
        mock_cohere_instance.embed_text_async = AsyncMock(return_value=test_embeddings)

        mock_qdrant_instance = Mock()
        mock_qdrant_instance.collection_name = "test_collection"
        mock_qdrant_instance.upsert_embeddings_batch.return_value = True

        mock_cohere.return_value = mock_cohere_instance
        mock_qdrant.return_value = mock_qdrant_instance

        # Create service instance
        service = EmbeddingService()

        # Create test chunks
        chunks = [
            DocumentChunk(
                id="chunk1",
                content="This is test content for embedding.",
                source_file_path="test.md",
                chunk_index=0,
                character_position=0,
                content_hash="hash1",
                chunk_size_tokens=100,
                created_at=datetime.now()
            ),
            DocumentChunk(
                id="chunk2",
                content="This is more test content for embedding.",
                source_file_path="test.md",
                chunk_index=1,
                character_position=50,
                content_hash="hash2",
                chunk_size_tokens=100,
                created_at=datetime.now()
            )
        ]

        # Execute the full process
        result = await service.process_and_store_chunks(chunks)

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_processed"], 2)
        self.assertEqual(result["embeddings_generated"], 2)

        # Verify that Cohere was called appropriately
        self.assertEqual(mock_cohere_instance.embed_text_async.call_count, 2)  # Called for each chunk in batch

        # Verify that Qdrant was called to store the results
        mock_qdrant_instance.upsert_embeddings_batch.assert_called_once()


if __name__ == '__main__':
    unittest.main()