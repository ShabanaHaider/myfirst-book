"""
Script to check if data is available in Qdrant after RAG system tasks completion.
"""
import asyncio
import logging
from src.clients.qdrant_client import QdrantWrapper
from src.config.settings import settings


def setup_logging():
    """Set up logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def check_qdrant_connection():
    """Check if we can connect to Qdrant."""
    print("Checking Qdrant connection...")

    try:
        qdrant_client = QdrantWrapper()
        is_healthy = qdrant_client.health_check()

        if is_healthy:
            print("+ Successfully connected to Qdrant")
            return qdrant_client
        else:
            print("- Failed to connect to Qdrant")
            return None
    except Exception as e:
        print(f"- Error connecting to Qdrant: {e}")
        return None


async def check_collection_status(qdrant_client):
    """Check the status of the collection."""
    print(f"\nChecking collection: {qdrant_client.collection_name}")

    try:
        # Check if collection exists
        collections = qdrant_client.client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if qdrant_client.collection_name in collection_names:
            print(f"+ Collection '{qdrant_client.collection_name}' exists")

            # Count the points in the collection
            count = qdrant_client.count_points()
            print(f"+ Total vectors in collection: {count}")

            if count > 0:
                print("+ Data is available in Qdrant!")
                print(f"  The RAG system has successfully stored {count} vectors.")
                print("  You can now query the system to retrieve information.")
                return True
            else:
                print("! Collection exists but is empty.")
                print("  The ingestion process may not have been run yet.")
                return False
        else:
            print(f"- Collection '{qdrant_client.collection_name}' does not exist")
            print("  You need to run the ingestion process to create the collection and store data.")
            return False

    except Exception as e:
        print(f"- Error checking collection status: {e}")
        return False


async def check_sample_data(qdrant_client):
    """Check sample data in the collection."""
    print(f"\nRetrieving sample data from Qdrant...")

    try:
        # Get collection info
        collection_info = qdrant_client.client.get_collection(qdrant_client.collection_name)
        print(f"Collection vectors count: {collection_info.points_count}")
        print(f"Collection vectors config: {collection_info.config.params}")

        # Try to retrieve a few points if they exist
        if collection_info.points_count > 0:
            # Limit to 3 sample points to avoid too much output
            limit = min(3, collection_info.points_count)
            points = qdrant_client.client.scroll(
                collection_name=qdrant_client.collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            print(f"\nSample of {limit} stored vectors:")
            # Handle the return value from scroll method - it could be (points, next_offset) or just points
            if isinstance(points, tuple):
                points_list = points[0]
            else:
                points_list = points

            for i, point in enumerate(points_list):
                # Handle both potential formats: PointStruct or dict-like structure
                if hasattr(point, 'id'):
                    point_id = point.id
                    payload = point.payload
                else:
                    # Assume it's a tuple (id, payload) or dict-like
                    if isinstance(point, tuple) and len(point) == 2:
                        point_id, payload = point
                    elif isinstance(point, dict):
                        point_id = point.get('id', 'Unknown')
                        payload = point.get('payload', {})
                    else:
                        # If we can't parse it, skip this point
                        continue

                print(f"  {i+1}. ID: {point_id}")
                print(f"     Source: {payload.get('source_file_path', 'Unknown')}")
                print(f"     Content hash: {payload.get('content_hash', 'Unknown')[:10]}...")
                print(f"     Chunk index: {payload.get('chunk_index', 'Unknown')}")
                print()

        return True

    except Exception as e:
        print(f"- Error retrieving sample data: {e}")
        return False


async def main():
    """Main function to check Qdrant data availability."""
    print("=" * 60)
    print("Qdrant Data Availability Checker")
    print("For RAG Chatbot System")
    print("=" * 60)

    setup_logging()

    # Check Qdrant connection
    qdrant_client = await check_qdrant_connection()
    if not qdrant_client:
        print("\nCannot proceed without Qdrant connection.")
        return

    # Check collection status
    has_data = await check_collection_status(qdrant_client)

    if has_data:
        # Show sample data if available
        await check_sample_data(qdrant_client)

        print("\n" + "=" * 60)
        print("CONCLUSION: Data is available in Qdrant!")
        print("=" * 60)
        print("+ The RAG system has successfully stored vectors in Qdrant")
        print("+ You can now use the query functionality to retrieve information")
        print("+ Your ingestion process completed successfully")
    else:
        print("\n" + "=" * 60)
        print("CONCLUSION: No data found in Qdrant")
        print("=" * 60)
        print("Possible reasons:")
        print("  1. The ingestion process hasn't been run yet")
        print("  2. The ingestion process failed")
        print("  3. The Qdrant collection was not created properly")
        print("\nTo fix this:")
        print("  1. Make sure Qdrant is running")
        print("  2. Run the ingestion process: python -m src.main --ingest")
        print("  3. Verify your document files are in the correct directory")


if __name__ == "__main__":
    asyncio.run(main())