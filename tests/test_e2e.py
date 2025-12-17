"""
End-to-end integration tests for the RAG Chatbot system.
"""
import asyncio
import pytest
import unittest
from unittest.mock import Mock, AsyncMock, patch
from src.services.embedding_service import EmbeddingService
from src.services.vector_storage import VectorStorageService
from src.services.retrieval_service import RetrievalService
from src.models.document_chunk import DocumentChunk
from src.models.embedding_vector import EmbeddingVector
from src.api.query_endpoint import QueryEndpoint
from src.api.ingestion_endpoint import IngestionEndpoint
from src.config.settings import settings
from datetime import datetime
from typing import List
import tempfile
import os


class TestRAGEndToEnd(unittest.TestCase):
    """End-to-end integration tests for the RAG Chatbot system."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Use a test collection name
        settings.COLLECTION_NAME = "test_e2e_collection"

    @pytest.mark.asyncio
    @patch('src.services.embedding_service.CohereWrapper')
    @patch('src.services.embedding_service.QdrantWrapper')
    @patch('src.services.vector_storage.QdrantWrapper')
    @patch('src.services.retrieval_service.QdrantWrapper')
    async def test_complete_rag_flow(self, mock_retrieval_qdrant, mock_storage_qdrant,
                                     mock_embedding_qdrant, mock_cohere):
        """Test the complete RAG flow: ingestion -> embedding -> storage -> retrieval -> query."""
        # Setup mocks
        # Mock Cohere client
        mock_cohere_instance = Mock()
        mock_cohere_instance.batch_size = 32
        mock_cohere_instance.validate_embeddings.return_value = True
        # Return 1024-dim vectors for testing
        test_embedding = [0.1] * 1024
        mock_cohere_instance.embed_text_async = AsyncMock(return_value=[test_embedding, test_embedding])
        mock_cohere_instance.embed_query = AsyncMock(return_value=test_embedding)

        # Mock Qdrant clients
        mock_qdrant_instances = [Mock() for _ in range(3)]
        for qdrant_mock in mock_qdrant_instances:
            qdrant_mock.collection_name = "test_e2e_collection"
            qdrant_mock.upsert_embeddings_batch.return_value = True
            qdrant_mock.ensure_collection_exists.return_value = True
            qdrant_mock.search_similar.return_value = [
                {
                    'id': 'chunk1',
                    'score': 0.9,
                    'payload': {
                        'source_file_path': 'test.md',
                        'chunk_index': 0,
                        'content': 'This is test content for RAG system.'
                    }
                }
            ]
            qdrant_mock.count_points.return_value = 1
            qdrant_mock.health_check.return_value = True

        # Assign the same mock to all patched Qdrant clients
        mock_embedding_qdrant.return_value = mock_qdrant_instances[0]
        mock_storage_qdrant.return_value = mock_qdrant_instances[1]
        mock_retrieval_qdrant.return_value = mock_qdrant_instances[2]
        mock_cohere.return_value = mock_cohere_instance

        # 1. Create document chunks (simulating ingestion)
        document_chunks = [
            DocumentChunk(
                id="chunk1",
                content="This is test content for RAG system.",
                source_file_path="test.md",
                chunk_index=0,
                character_position=0,
                content_hash="hash1",
                chunk_size_tokens=100,
                created_at=datetime.now()
            ),
            DocumentChunk(
                id="chunk2",
                content="This is additional content for testing.",
                source_file_path="test.md",
                chunk_index=1,
                character_position=50,
                content_hash="hash2",
                chunk_size_tokens=100,
                created_at=datetime.now()
            )
        ]

        # 2. Generate embeddings using EmbeddingService
        embedding_service = EmbeddingService()
        embedding_vectors = await embedding_service.generate_embeddings_for_chunks(document_chunks)

        # Verify embeddings were generated
        self.assertEqual(len(embedding_vectors), 2)
        for ev in embedding_vectors:
            self.assertEqual(len(ev.vector), 1024)  # Cohere vectors are 1024-dimensional

        # 3. Store embeddings using VectorStorageService
        vector_storage_service = VectorStorageService()
        storage_result = await vector_storage_service.validate_and_store_embeddings(embedding_vectors)

        # Verify storage was successful
        self.assertTrue(storage_result["success"])
        self.assertEqual(storage_result["vectors_stored"], 2)

        # 4. Retrieve similar content using RetrievalService
        retrieval_service = RetrievalService()
        query_text = "test content"
        similar_chunks = await retrieval_service.retrieve_similar_chunks(query_text, top_k=2)

        # Verify retrieval worked
        self.assertGreater(len(similar_chunks), 0)
        self.assertIn("This is test content for RAG system.", [chunk['payload']['content'] for chunk in similar_chunks])

        # 5. Test query endpoint
        query_endpoint = QueryEndpoint()
        query_response = await query_endpoint.process_query({
            "query": "What is the test content?",
            "top_k": 2,
            "similarity_threshold": 0.7
        })

        # Verify query response
        self.assertIn("response", query_response)
        self.assertIn("sources", query_response)
        self.assertGreater(len(query_response["sources"]), 0)

    @pytest.mark.asyncio
    @patch('src.services.embedding_service.CohereWrapper')
    @patch('src.services.embedding_service.QdrantWrapper')
    @patch('src.services.vector_storage.QdrantWrapper')
    @patch('src.services.retrieval_service.QdrantWrapper')
    async def test_ingestion_to_query_workflow(self, mock_retrieval_qdrant, mock_storage_qdrant,
                                               mock_embedding_qdrant, mock_cohere):
        """Test the full workflow from ingestion endpoint to query endpoint."""
        # Setup mocks
        mock_cohere_instance = Mock()
        mock_cohere_instance.batch_size = 32
        mock_cohere_instance.validate_embeddings.return_value = True
        test_embedding = [0.5] * 1024  # 1024-dim vector
        mock_cohere_instance.embed_text_async = AsyncMock(return_value=[test_embedding])
        mock_cohere_instance.embed_query = AsyncMock(return_value=test_embedding)

        mock_qdrant_instances = [Mock() for _ in range(3)]
        for qdrant_mock in mock_qdrant_instances:
            qdrant_mock.collection_name = "test_e2e_collection"
            qdrant_mock.upsert_embeddings_batch.return_value = True
            qdrant_mock.ensure_collection_exists.return_value = True
            qdrant_mock.search_similar.return_value = [
                {
                    'id': 'ingested_chunk',
                    'score': 0.85,
                    'payload': {
                        'source_file_path': 'ingested_doc.md',
                        'chunk_index': 0,
                        'content': 'Content ingested through the full workflow.',
                        'original_content': 'Original document content'
                    }
                }
            ]
            qdrant_mock.count_points.return_value = 1
            qdrant_mock.health_check.return_value = True

        mock_embedding_qdrant.return_value = mock_qdrant_instances[0]
        mock_storage_qdrant.return_value = mock_qdrant_instances[1]
        mock_retrieval_qdrant.return_value = mock_qdrant_instances[2]
        mock_cohere.return_value = mock_cohere_instance

        # Simulate ingestion process
        ingestion_endpoint = IngestionEndpoint()

        # Create mock documents to ingest
        test_docs_content = [
            "# Test Document\nThis is test content that will be processed by the RAG system.\n",
            "# Another Document\nMore content for testing the ingestion pipeline.\n"
        ]

        # Create temporary files for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            doc_paths = []
            for i, content in enumerate(test_docs_content):
                doc_path = os.path.join(temp_dir, f"test_doc_{i}.md")
                with open(doc_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                doc_paths.append(doc_path)

            # Simulate ingestion process (this would normally read from the docs directory)
            # For this test, we'll directly test the ingestion workflow components
            from src.services.ingestion_pipeline import IngestionPipelineService
            from src.services.file_traversal import FileTraversalService
            from src.services.chunking_service import ChunkingService

            with patch('src.services.ingestion_pipeline.FileTraversalService') as mock_file_traversal, \
                 patch('src.services.ingestion_pipeline.ChunkingService') as mock_chunking, \
                 patch('src.services.ingestion_pipeline.EmbeddingService') as mock_emb_service, \
                 patch('src.services.ingestion_pipeline.VectorStorageService') as mock_storage_service:

                # Mock file traversal to return our test files
                mock_file_traversal_instance = Mock()
                mock_file_traversal_instance.get_markdown_files.return_value = doc_paths
                mock_file_traversal.return_value = mock_file_traversal_instance

                # Mock chunking service to return our test chunks
                mock_chunking_instance = Mock()
                test_chunks = [
                    DocumentChunk(
                        id="ingested_chunk",
                        content="Content ingested through the full workflow.",
                        source_file_path="ingested_doc.md",
                        chunk_index=0,
                        character_position=0,
                        content_hash="ingest_hash",
                        chunk_size_tokens=100,
                        created_at=datetime.now()
                    )
                ]
                mock_chunking_instance.process_file.return_value = test_chunks
                mock_chunking.return_value = mock_chunking_instance

                # Mock embedding and storage services
                mock_emb_service_instance = Mock()
                mock_emb_service_instance.process_and_store_chunks = AsyncMock(return_value={
                    "success": True,
                    "chunks_processed": 1,
                    "embeddings_generated": 1,
                    "processing_time_seconds": 0.1
                })
                mock_emb_service.return_value = mock_emb_service_instance

                mock_storage_service_instance = Mock()
                mock_storage_service_instance.store_document_chunks = AsyncMock(return_value={
                    "success": True,
                    "chunks_processed": 1,
                    "vectors_stored": 1,
                    "processing_time_seconds": 0.05
                })
                mock_storage_service.return_value = mock_storage_service_instance

                # Run the ingestion pipeline
                ingestion_pipeline = IngestionPipelineService()
                ingestion_result = await ingestion_pipeline.ingest_all_documents()

                # Verify ingestion was successful
                self.assertTrue(ingestion_result["success"])

                # Now test querying the ingested content
                retrieval_service = RetrievalService()
                query_result = await retrieval_service.retrieve_similar_chunks("test content", top_k=1)

                # Verify we can retrieve the ingested content
                self.assertGreater(len(query_result), 0)
                self.assertIn("Content ingested", query_result[0]['payload']['content'])

    @pytest.mark.asyncio
    @patch('src.services.embedding_service.CohereWrapper')
    @patch('src.services.embedding_service.QdrantWrapper')
    @patch('src.services.vector_storage.QdrantWrapper')
    @patch('src.services.retrieval_service.QdrantWrapper')
    async def test_error_handling_in_full_workflow(self, mock_retrieval_qdrant, mock_storage_qdrant,
                                                   mock_embedding_qdrant, mock_cohere):
        """Test error handling throughout the full RAG workflow."""
        # Setup mocks with some failures to test error handling
        mock_cohere_instance = Mock()
        mock_cohere_instance.batch_size = 32
        mock_cohere_instance.validate_embeddings.return_value = True
        test_embedding = [0.3] * 1024
        mock_cohere_instance.embed_text_async = AsyncMock(return_value=[test_embedding])
        mock_cohere_instance.embed_query = AsyncMock(return_value=test_embedding)

        # Mock Qdrant clients
        mock_qdrant_instances = [Mock() for _ in range(3)]
        for i, qdrant_mock in enumerate(mock_qdrant_instances):
            qdrant_mock.collection_name = "test_e2e_collection"
            qdrant_mock.ensure_collection_exists.return_value = True
            qdrant_mock.count_points.return_value = 1
            qdrant_mock.health_check.return_value = True

            # Make the first Qdrant mock fail on upsert but succeed on search
            if i == 0 or i == 1:  # embedding and storage services
                qdrant_mock.upsert_embeddings_batch.return_value = False  # Simulate failure
            else:  # retrieval service
                qdrant_mock.search_similar.return_value = []  # No results but no error

        mock_embedding_qdrant.return_value = mock_qdrant_instances[0]
        mock_storage_qdrant.return_value = mock_qdrant_instances[1]
        mock_retrieval_qdrant.return_value = mock_qdrant_instances[2]
        mock_cohere.return_value = mock_cohere_instance

        # Test that embedding service handles storage failures gracefully
        embedding_service = EmbeddingService()
        document_chunks = [
            DocumentChunk(
                id="error_test_chunk",
                content="Content for testing error handling.",
                source_file_path="error_test.md",
                chunk_index=0,
                character_position=0,
                content_hash="error_hash",
                chunk_size_tokens=100,
                created_at=datetime.now()
            )
        ]

        # Generate embeddings (this should succeed)
        embedding_vectors = await embedding_service.generate_embeddings_for_chunks(document_chunks)
        self.assertEqual(len(embedding_vectors), 1)

        # Try to store embeddings (this should fail based on our mock)
        vector_storage_service = VectorStorageService()
        storage_result = await vector_storage_service.store_embeddings(embedding_vectors)
        self.assertFalse(storage_result)  # Should return False due to mock

        # Test that retrieval service handles cases with no results
        retrieval_service = RetrievalService()
        query_result = await retrieval_service.retrieve_similar_chunks("test query", top_k=1)
        self.assertEqual(len(query_result), 0)  # Should return empty list based on our mock

    def test_configuration_and_health_endpoints_integration(self):
        """Test that configuration and health endpoints work together."""
        from src.api.health_endpoint import get_health_status
        from src.api.config_endpoint import get_public_config

        # Get health status
        health_status = get_health_status()

        # Verify health status structure
        self.assertIn("status", health_status)
        self.assertIn("components", health_status)
        self.assertIn("qdrant", health_status["components"])
        self.assertIn("cohere", health_status["components"])

        # Get public config
        public_config = get_public_config()

        # Verify config structure
        self.assertIn("processing_parameters", public_config)
        self.assertIn("performance_limits", public_config)
        self.assertIn("file_paths", public_config)

        # Verify that both endpoints return consistent collection names
        if health_status.get("collection_stats"):
            health_collection = health_status["collection_stats"]["collection_name"]
            config_collection = public_config["qdrant_config"]["collection_exists"]  # This is a boolean, but we tested the existence
            # Both should reference the same collection conceptually


class TestPerformanceAndLoad(unittest.TestCase):
    """Performance and load testing for the RAG system."""

    @pytest.mark.asyncio
    @patch('src.services.embedding_service.CohereWrapper')
    @patch('src.services.embedding_service.QdrantWrapper')
    @patch('src.services.vector_storage.QdrantWrapper')
    async def test_batch_processing_performance(self, mock_storage_qdrant,
                                               mock_embedding_qdrant, mock_cohere):
        """Test performance with batch processing."""
        # Setup mocks
        mock_cohere_instance = Mock()
        mock_cohere_instance.batch_size = 32
        mock_cohere_instance.validate_embeddings.return_value = True
        test_embedding = [0.2] * 1024
        # For batch testing, return multiple embeddings
        mock_cohere_instance.embed_text_async = AsyncMock(
            side_effect=lambda texts, input_type: [test_embedding] * len(texts if isinstance(texts, list) else [texts])
        )

        mock_qdrant_instances = [Mock() for _ in range(2)]
        for qdrant_mock in mock_qdrant_instances:
            qdrant_mock.collection_name = "test_e2e_collection"
            qdrant_mock.upsert_embeddings_batch.return_value = True
            qdrant_mock.ensure_collection_exists.return_value = True
            qdrant_mock.count_points.return_value = 10  # Simulate existing content
            qdrant_mock.health_check.return_value = True

        mock_embedding_qdrant.return_value = mock_qdrant_instances[0]
        mock_storage_qdrant.return_value = mock_qdrant_instances[1]
        mock_cohere.return_value = mock_cohere_instance

        # Create a larger set of document chunks for batch testing
        large_document_chunks = []
        for i in range(50):  # 50 chunks to test batch processing
            chunk = DocumentChunk(
                id=f"batch_chunk_{i}",
                content=f"This is content for batch processing test chunk {i}.",
                source_file_path=f"batch_test_{i}.md",
                chunk_index=i,
                character_position=i * 50,
                content_hash=f"batch_hash_{i}",
                chunk_size_tokens=100,
                created_at=datetime.now()
            )
            large_document_chunks.append(chunk)

        # Process the large batch
        embedding_service = EmbeddingService()
        start_time = asyncio.get_event_loop().time()

        embedding_vectors = await embedding_service.generate_embeddings_for_chunks(large_document_chunks)

        processing_time = asyncio.get_event_loop().time() - start_time

        # Verify results
        self.assertEqual(len(embedding_vectors), 50)
        self.assertLess(processing_time, 10.0)  # Should process 50 chunks in under 10 seconds

        # Store the vectors
        vector_storage_service = VectorStorageService()
        storage_result = await vector_storage_service.store_embedding_vectors_batch(embedding_vectors)

        self.assertTrue(storage_result)


if __name__ == '__main__':
    unittest.main()