"""
Script to run the RAG Chatbot ingestion process and populate Qdrant with data.
"""
import asyncio
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate environment variables
required_vars = ['COHERE_API_KEY']
if not os.getenv('QDRANT_URL'):
    required_vars.extend(['QDRANT_HOST', 'QDRANT_PORT'])  # Either URL or host/port is needed

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {missing_vars}")
    logger.error("Please set these in your .env file before running ingestion")
    exit(1)

# Import after environment is loaded to ensure settings are properly configured
try:
    from src.services.ingestion_pipeline import IngestionPipelineService
    from src.api.health_endpoint import get_health_status
    from src.api.config_endpoint import get_public_config
    from src.clients.qdrant_client import QdrantWrapper
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure all dependencies are installed: pip install -r requirements.txt")
    exit(1)


async def check_system_health():
    """Check if all system components are healthy before ingestion."""
    logger.info("Checking system health before ingestion...")

    health_status = get_health_status()
    logger.info(f"System health status: {health_status['status']}")

    if health_status['status'] != 'healthy':
        logger.warning("Some system components are not healthy:")
        for component, status in health_status['components'].items():
            logger.warning(f"  - {component}: {status['status']}")
        return False

    # Show configuration
    config = get_public_config()
    logger.info(f"Using collection: {config['processing_parameters']['collection_name']}")
    logger.info(f"Processing directory: {config['file_paths']['docs_directory']}")

    return True


async def run_ingestion():
    """Run the ingestion process to populate Qdrant with document vectors."""
    logger.info("Starting RAG Chatbot ingestion process...")

    # Check system health first
    if not await check_system_health():
        logger.error("System is not healthy. Please fix the issues before running ingestion.")
        return False

    try:
        # Create ingestion pipeline service
        ingestion_pipeline = IngestionPipelineService()

        # Get the docs directory from settings
        from src.config.settings import settings
        docs_directory = settings.DOCS_DIRECTORY
        logger.info(f"Scanning documents in: {docs_directory}")

        # Check if the directory exists and has files
        import os
        if not os.path.exists(docs_directory):
            logger.error(f"Documents directory does not exist: {docs_directory}")
            return False

        # Count markdown files
        import glob
        markdown_files = glob.glob(f"{docs_directory}/**/*.md", recursive=True)

        logger.info(f"Found {len(markdown_files)} markdown files to process")
        if markdown_files:
            logger.info("Sample files to be processed:")
            for file in markdown_files[:5]:  # Show first 5 files
                logger.info(f"  - {file}")
            if len(markdown_files) > 5:
                logger.info(f"  ... and {len(markdown_files) - 5} more files")

        # Run the ingestion process
        logger.info("Starting ingestion pipeline...")
        result = await ingestion_pipeline.run_ingestion_pipeline(docs_directory)

        logger.info(f"Ingestion completed with result: {result}")

        if result.get('success'):
            # Check Qdrant to confirm data was stored
            qdrant_client = QdrantWrapper()
            count = qdrant_client.count_points()
            logger.info(f"✓ Successfully stored {count} vectors in Qdrant collection: {qdrant_client.collection_name}")

            # Show sample of what was ingested
            if count > 0:
                logger.info("Data is now available in Qdrant and ready for querying!")
                return True
            else:
                logger.warning("Ingestion reported success but no vectors were stored in Qdrant")
                return False
        else:
            logger.error(f"Ingestion failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        logger.error(f"Error during ingestion: {e}", exc_info=True)
        return False


async def run_sample_query():
    """Run a sample query to test the system after ingestion."""
    logger.info("Running sample query to test the system...")

    try:
        from src.api.query_endpoint import QueryEndpoint

        query_endpoint = QueryEndpoint()
        sample_query = {
            "query": "What is this book about?",
            "top_k": 3,
            "similarity_threshold": 0.7
        }

        result = await query_endpoint.process_query(sample_query)
        logger.info(f"Sample query result: {result}")

        if result.get('response'):
            logger.info("✓ Query system is working correctly!")
            return True
        else:
            logger.info("Query returned no results (this may be normal if no data was ingested)")
            return False

    except Exception as e:
        logger.error(f"Error running sample query: {e}", exc_info=True)
        return False


async def main():
    """Main function to run the ingestion process."""
    logger.info("=" * 60)
    logger.info("RAG Chatbot - Document Ingestion Process")
    logger.info("=" * 60)

    # Instructions for user
    logger.info("Before running this script, make sure:")
    logger.info("1. You have a running Qdrant instance (local or cloud)")
    logger.info("2. Your API keys are set in the .env file")
    logger.info("3. The documents directory contains markdown files")
    logger.info("")

    # Check if Qdrant is accessible
    try:
        qdrant_client = QdrantWrapper()
        if qdrant_client.health_check():
            logger.info("+ Qdrant connection: OK")
        else:
            logger.error("- Qdrant connection: FAILED")
            logger.error("Please ensure Qdrant is running and credentials are correct")
            return
    except Exception as e:
        logger.error(f"- Qdrant connection failed: {e}")
        logger.error("Please ensure Qdrant is running and credentials are correct")
        return

    # Run ingestion
    ingestion_success = await run_ingestion()

    if ingestion_success:
        logger.info("\n" + "=" * 60)
        logger.info("INGESTION SUCCESSFUL!")
        logger.info("=" * 60)
        logger.info("Your documents have been processed and stored in Qdrant.")
        logger.info("You can now query the RAG system to retrieve information.")

        # Run a sample query to confirm everything works
        await run_sample_query()
    else:
        logger.info("\n" + "=" * 60)
        logger.info("INGESTION FAILED!")
        logger.info("=" * 60)
        logger.info("Please check the error messages above and try again.")
        logger.info("Common issues:")
        logger.info("- Invalid API keys")
        logger.info("- Qdrant not accessible")
        logger.info("- Documents directory doesn't exist or is empty")
        logger.info("- Network connectivity issues")


if __name__ == "__main__":
    # Run the asyncio event loop
    asyncio.run(main())