"""
Main entry point for the RAG Chatbot system.

This script demonstrates the complete workflow of the RAG system:
1. Ingestion of documents
2. Embedding generation
3. Storage in Qdrant
4. Querying with retrieval and generation
"""
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List

# Import all the necessary components
from src.services.ingestion_pipeline import IngestionPipelineService
from src.services.embedding_service import EmbeddingService
from src.services.vector_storage import VectorStorageService
from src.services.retrieval_service import RetrievalService
from src.query.query_processor import QueryProcessor
from src.query.response_generator import ResponseGenerator
from src.api.health_endpoint import get_health_status
from src.api.config_endpoint import get_public_config
from src.models.document_chunk import DocumentChunk
from src.clients.qdrant_client import QdrantWrapper
from src.config.settings import settings


def setup_logging():
    """Set up logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def run_ingestion_pipeline(docs_directory: str = None):
    """Run the complete ingestion pipeline."""
    print("Starting ingestion pipeline...")

    ingestion_pipeline = IngestionPipelineService()

    # Use provided directory or default from settings
    directory = docs_directory or settings.DOCS_DIRECTORY

    result = await ingestion_pipeline.ingest_all_documents(source_directory=directory)

    print(f"Ingestion completed: {result}")
    return result


async def run_sample_query(query_text: str):
    """Run a sample query against the RAG system."""
    print(f"Running query: '{query_text}'")

    # Use the retrieval service to test querying
    retrieval_service = RetrievalService()
    result = await retrieval_service.retrieve_similar_documents(query_text, top_k=3, similarity_threshold=0.7)

    print(f"Query result: {result}")
    return result


async def check_qdrant_data():
    """Check the data stored in Qdrant."""
    print("Checking Qdrant collection status...")

    qdrant_client = QdrantWrapper()

    # Get collection statistics
    count = qdrant_client.count_points()
    print(f"Total vectors in collection '{qdrant_client.collection_name}': {count}")

    # If there are vectors, get a sample
    if count > 0:
        # Try to retrieve a few points to verify data exists
        try:
            # This would require actual point IDs, so we'll just report the count
            print(f"✓ Data is available in Qdrant collection: {qdrant_client.collection_name}")
        except Exception as e:
            print(f"Error retrieving sample data: {e}")
    else:
        print(f"! No data found in Qdrant collection: {qdrant_client.collection_name}")

    return {"total_points": count, "collection_name": qdrant_client.collection_name}


async def run_health_check():
    """Run a health check on the system."""
    print("Running health check...")

    health_status = get_health_status()
    print(f"System health: {health_status['status']}")

    if health_status['status'] == 'healthy':
        print("✓ All system components are healthy")
    else:
        print("⚠ Some system components are unhealthy")
        for component, status in health_status['components'].items():
            print(f"  - {component}: {status['status']}")

    return health_status


async def show_config():
    """Show the current system configuration."""
    print("Current system configuration:")

    config = get_public_config()

    print(f"  - Collection name: {config['qdrant_config']['collection_exists']}")
    print(f"  - Chunk size tokens: {config['processing_parameters']['chunk_size_tokens']}")
    print(f"  - Top K retrieval: {config['processing_parameters']['top_k_retrieval']}")
    print(f"  - Similarity threshold: {config['processing_parameters']['similarity_threshold']}")
    print(f"  - Docs directory: {config['file_paths']['docs_directory']}")

    return config


async def demo_workflow():
    """Run a complete demo workflow."""
    print("=" * 60)
    print("RAG Chatbot System - Complete Workflow Demo")
    print("=" * 60)

    # 1. Show current config
    await show_config()

    # 2. Run health check
    health = await run_health_check()
    if health['status'] != 'healthy':
        print("⚠ System is not healthy. Please check configuration.")
        return

    # 3. Check current Qdrant data
    qdrant_status = await check_qdrant_data()

    # 4. Run ingestion (this would typically ingest from docs directory)
    # For demo purposes, we'll show what would happen
    print("\nTo run actual ingestion, call: await run_ingestion_pipeline()")
    print("This would:")
    print("  - Scan the docs directory for markdown files")
    print("  - Extract and chunk the content")
    print("  - Generate embeddings using Cohere")
    print("  - Store the vectors in Qdrant")

    # 5. Show what a query would look like
    print("\nTo run a query, call: await run_sample_query('your question here')")
    print("This would:")
    print("  - Convert the query to an embedding")
    print("  - Search for similar vectors in Qdrant")
    print("  - Retrieve relevant document chunks")
    print("  - Generate a response based on the retrieved content")

    # 6. Check Qdrant again after potential ingestion
    print(f"\nAfter ingestion, Qdrant would contain {qdrant_status['total_points']} vectors")
    print("You would be able to see your data in Qdrant once ingestion is complete.")


def main():
    """Main entry point for the application."""
    setup_logging()

    parser = argparse.ArgumentParser(description='RAG Chatbot System')
    parser.add_argument('--demo', action='store_true', help='Run demo workflow')
    parser.add_argument('--ingest', action='store_true', help='Run ingestion pipeline')
    parser.add_argument('--query', type=str, help='Run a sample query')
    parser.add_argument('--check-data', action='store_true', help='Check Qdrant data status')
    parser.add_argument('--health', action='store_true', help='Run health check')
    parser.add_argument('--config', action='store_true', help='Show configuration')

    args = parser.parse_args()

    # Run the requested operation
    if args.demo:
        asyncio.run(demo_workflow())
    elif args.ingest:
        # Run the actual ingestion pipeline
        ingestion_pipeline = IngestionPipelineService()
        result = asyncio.run(ingestion_pipeline.run_ingestion_pipeline(settings.DOCS_DIRECTORY))
        print(f"Ingestion completed: {result}")
    elif args.query:
        # Run the actual sample query
        result = asyncio.run(run_sample_query(args.query))
        print(f"Query completed: {result}")
    elif args.check_data:
        asyncio.run(check_qdrant_data())
    elif args.health:
        asyncio.run(run_health_check())
    elif args.config:
        asyncio.run(show_config())
    else:
        print("RAG Chatbot System")
        print("Use --demo to run a complete workflow demonstration")
        print("Use --health to check system health")
        print("Use --config to see configuration")
        print("Use --check-data to check Qdrant data status")
        print("Use --ingest to run the ingestion pipeline")
        print("Use --query 'your question' to run a query")


if __name__ == "__main__":
    main()