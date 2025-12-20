"""
Integration tests for vector storage functionality.
"""
import asyncio
import pytest
import unittest
from unittest.mock import Mock, patch
from src.services.vector_storage import VectorStorageService
from src.models.embedding_vector import EmbeddingVector
from src.models.document_chunk import DocumentChunk
from datetime import datetime
from typing import List


class TestVectorStorageService(unittest.TestCase):
    """Integration tests for the VectorStorageService class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        with patch('src.services.vector_storage.QdrantWrapper') as mock_qdrant:

            # Mock the Qdrant client
            self.mock_qdrant_client = Mock()
            self.mock_qdrant_client.collection_name = "test_collection"
            self.mock_qdrant_client.upsert_embeddings_batch.return_value = True
            self.mock_qdrant_client.upsert_embedding.return_value = True
            self.mock_qdrant_client.ensure_collection_exists.return_value = True
            self.mock_qdrant_client.count_points.return_value = 10
            self.mock_qdrant_client.health_check.return_value = True
            self.mock_qdrant_client.delete_by_payload.return_value = True

            # Patch the constructor
            mock_qdrant.return_value = self.mock_qdrant_client

            self.vector_storage_service = VectorStorageService()

    def test_ensure_collection_exists(self):
        """Test ensuring the collection exists."""
        # This is called in __init__, so just verify it was called
        self.mock_qdrant_client.ensure_collection_exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_embedding_vector_success(self):
        """Test storing a single embedding vector successfully."""
        embedding_vector = EmbeddingVector(
            id="vector1",
            vector=[0.1, 0.2, 0.3] + [0.0] * 1021,  # 1024-dim vector
            metadata={"source_file_path": "test.md", "chunk_index": 0, "content_hash": "hash1"},
            collection_name="test_collection",
            created_at=datetime.now()
        )

        result = await self.vector_storage_service.store_embedding_vector(embedding_vector)

        self.assertTrue(result)
        self.mock_qdrant_client.upsert_embedding.assert_called_once_with(embedding_vector)

    @pytest.mark.asyncio
    async def test_store_embedding_vectors_batch_success(self):
        """Test storing multiple embedding vectors in a batch."""
        embedding_vectors = [
            EmbeddingVector(
                id="vector1",
                vector=[0.1, 0.2, 0.3] + [0.0] * 1021,  # 1024-dim vector
                metadata={"source_file_path": "test.md", "chunk_index": 0, "content_hash": "hash1"},
                collection_name="test_collection",
                created_at=datetime.now()
            ),
            EmbeddingVector(
                id="vector2",
                vector=[0.4, 0.5, 0.6] + [0.0] * 1021,  # 1024-dim vector
                metadata={"source_file_path": "test2.md", "chunk_index": 1, "content_hash": "hash2"},
                collection_name="test_collection",
                created_at=datetime.now()
            )
        ]

        result = await self.vector_storage_service.store_embedding_vectors_batch(embedding_vectors)

        self.assertTrue(result)
        self.mock_qdrant_client.upsert_embeddings_batch.assert_called_once_with(embedding_vectors)

    @pytest.mark.asyncio
    async def test_store_embedding_vectors_batch_empty(self):
        """Test storing an empty list of embedding vectors."""
        result = await self.vector_storage_service.store_embedding_vectors_batch([])
        self.assertTrue(result)  # Should return True for empty list

    @pytest.mark.asyncio
    async def test_store_document_chunks(self):
        """Test storing document chunks as embedding vectors."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                content="This is test content.",
                source_file_path="test.md",
                chunk_index=0,
                character_position=0,
                content_hash="hash1",
                chunk_size_tokens=100,
                created_at=datetime.now()
            )
        ]

        result = await self.vector_storage_service.store_document_chunks(chunks)

        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_processed"], 1)
        self.assertEqual(result["vectors_stored"], 1)

    @pytest.mark.asyncio
    async def test_incremental_upsert(self):
        """Test incremental upsert functionality."""
        embedding_vectors = [
            EmbeddingVector(
                id="vector1",
                vector=[0.1, 0.2, 0.3] + [0.0] * 1021,  # 1024-dim vector
                metadata={"source_file_path": "test.md", "chunk_index": 0, "content_hash": "hash1"},
                collection_name="test_collection",
                created_at=datetime.now()
            )
        ]

        result = await self.vector_storage_service.incremental_upsert(embedding_vectors)

        self.assertTrue(result["success"])
        self.assertEqual(result["vectors_upserted"], 1)

    @pytest.mark.asyncio
    async def test_validate_and_store_embeddings_success(self):
        """Test validating and storing embeddings."""
        embedding_vectors = [
            EmbeddingVector(
                id="vector1",
                vector=[0.1, 0.2, 0.3] + [0.0] * 1021,  # 1024-dim vector
                metadata={"source_file_path": "test.md", "chunk_index": 0, "content_hash": "hash1"},
                collection_name="test_collection",
                created_at=datetime.now()
            )
        ]

        result = await self.vector_storage_service.validate_and_store_embeddings(embedding_vectors)

        self.assertTrue(result["success"])
        self.assertEqual(result["vectors_validated"], 1)
        self.assertEqual(result["vectors_stored"], 1)

    @pytest.mark.asyncio
    async def test_validate_and_store_embeddings_invalid_dimensions(self):
        """Test validation failure with incorrect dimensions."""
        embedding_vectors = [
            EmbeddingVector(
                id="vector1",
                vector=[0.1, 0.2, 0.3],  # Only 3 dimensions instead of 1024
                metadata={"source_file_path": "test.md", "chunk_index": 0, "content_hash": "hash1"},
                collection_name="test_collection",
                created_at=datetime.now()
            )
        ]

        result = await self.vector_storage_service.validate_and_store_embeddings(embedding_vectors)

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    @pytest.mark.asyncio
    async def test_validate_and_store_embeddings_missing_metadata(self):
        """Test validation failure with missing metadata."""
        embedding_vectors = [
            EmbeddingVector(
                id="vector1",
                vector=[0.1, 0.2, 0.3] + [0.0] * 1021,  # 1024-dim vector
                metadata={"source_file_path": "test.md", "chunk_index": 0},  # Missing content_hash
                collection_name="test_collection",
                created_at=datetime.now()
            )
        ]

        result = await self.vector_storage_service.validate_and_store_embeddings(embedding_vectors)

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_get_collection_stats(self):
        """Test getting collection statistics."""
        stats = self.vector_storage_service.get_collection_stats()

        self.assertEqual(stats["total_points"], 10)
        self.assertEqual(stats["collection_name"], "test_collection")
        self.assertTrue(stats["healthy"])

    @pytest.mark.asyncio
    async def test_delete_by_source_file(self):
        """Test deleting vectors by source file path."""
        result = await self.vector_storage_service.delete_by_source_file("test.md")

        self.assertTrue(result)
        self.mock_qdrant_client.delete_by_payload.assert_called_once_with("source_file_path", "test.md")


class TestVectorStorageIntegration(unittest.TestCase):
    """Integration tests for vector storage with actual Qdrant interactions."""

    @pytest.mark.asyncio
    @patch('src.services.vector_storage.QdrantWrapper')
    async def test_complete_storage_workflow(self, mock_qdrant):
        """Test the complete workflow from document chunks to Qdrant storage."""
        # Setup mock
        mock_qdrant_instance = Mock()
        mock_qdrant_instance.collection_name = "myfirst_book"
        mock_qdrant_instance.upsert_embeddings_batch.return_value = True
        mock_qdrant_instance.ensure_collection_exists.return_value = True
        mock_qdrant_instance.count_points.return_value = 5
        mock_qdrant_instance.health_check.return_value = True

        mock_qdrant.return_value = mock_qdrant_instance

        # Create service instance
        service = VectorStorageService()

        # Create multiple document chunks
        chunks = [
            DocumentChunk(
                id="chunk1",
                content="First chunk of content for testing.",
                source_file_path="docs/intro.md",
                chunk_index=0,
                character_position=0,
                content_hash="hash1",
                chunk_size_tokens=100,
                created_at=datetime.now()
            ),
            DocumentChunk(
                id="chunk2",
                content="Second chunk of content for testing.",
                source_file_path="docs/intro.md",
                chunk_index=1,
                character_position=50,
                content_hash="hash2",
                chunk_size_tokens=100,
                created_at=datetime.now()
            ),
            DocumentChunk(
                id="chunk3",
                content="Third chunk of content from a different file.",
                source_file_path="docs/advanced.md",
                chunk_index=0,
                character_position=0,
                content_hash="hash3",
                chunk_size_tokens=100,
                created_at=datetime.now()
            )
        ]

        # Execute the storage workflow
        result = await service.store_document_chunks(chunks)

        # Verify the results
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_processed"], 3)
        self.assertEqual(result["vectors_stored"], 3)
        self.assertEqual(result["collection_name"], "myfirst_book")

        # Verify that Qdrant was called appropriately
        mock_qdrant_instance.upsert_embeddings_batch.assert_called_once()
        call_args = mock_qdrant_instance.upsert_embeddings_batch.call_args[0][0]
        self.assertEqual(len(call_args), 3)  # 3 embedding vectors created

        # Verify each embedding vector has proper metadata
        for i, embedding_vector in enumerate(call_args):
            self.assertIsInstance(embedding_vector, EmbeddingVector)
            self.assertEqual(embedding_vector.metadata["source_file_path"], chunks[i].source_file_path)
            self.assertEqual(embedding_vector.metadata["chunk_index"], chunks[i].chunk_index)
            self.assertEqual(embedding_vector.metadata["content_hash"], chunks[i].content_hash)

    @pytest.mark.asyncio
    @patch('src.services.vector_storage.QdrantWrapper')
    async def test_incremental_storage_with_validation(self, mock_qdrant):
        """Test incremental storage with validation."""
        # Setup mock
        mock_qdrant_instance = Mock()
        mock_qdrant_instance.collection_name = "myfirst_book"
        mock_qdrant_instance.upsert_embeddings_batch.return_value = True
        mock_qdrant_instance.ensure_collection_exists.return_value = True

        mock_qdrant.return_value = mock_qdrant_instance

        # Create service instance
        service = VectorStorageService()

        # Create embedding vectors with valid dimensions and metadata
        embedding_vectors = [
            EmbeddingVector(
                id="vector1",
                vector=[0.1] * 1024,  # Valid 1024-dim vector
                metadata={
                    "source_file_path": "docs/test.md",
                    "chunk_index": 0,
                    "content_hash": "hash1",
                    "original_content_length": 50,
                    "chunk_size_tokens": 100
                },
                collection_name="myfirst_book",
                created_at=datetime.now()
            ),
            EmbeddingVector(
                id="vector2",
                vector=[0.2] * 1024,  # Valid 1024-dim vector
                metadata={
                    "source_file_path": "docs/test.md",
                    "chunk_index": 1,
                    "content_hash": "hash2",
                    "original_content_length": 60,
                    "chunk_size_tokens": 100
                },
                collection_name="myfirst_book",
                created_at=datetime.now()
            )
        ]

        # Execute validation and storage
        result = await service.validate_and_store_embeddings(embedding_vectors)

        # Verify the results
        self.assertTrue(result["success"])
        self.assertEqual(result["vectors_validated"], 2)
        self.assertEqual(result["vectors_stored"], 2)

        # Verify that Qdrant was called to store the vectors
        mock_qdrant_instance.upsert_embeddings_batch.assert_called_once()
        call_args = mock_qdrant_instance.upsert_embeddings_batch.call_args[0][0]
        self.assertEqual(len(call_args), 2)


if __name__ == '__main__':
    unittest.main()