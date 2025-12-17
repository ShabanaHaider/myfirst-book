#!/usr/bin/env python3
"""
Script to reset the Qdrant collection with correct dimensions.
"""

import asyncio
from src.clients.qdrant_client import QdrantWrapper


async def reset_collection():
    """Reset the Qdrant collection with correct dimensions."""
    print("Connecting to Qdrant...")
    qdrant_client = QdrantWrapper()

    print(f"Deleting existing collection: {qdrant_client.collection_name}")
    success = qdrant_client.delete_collection()

    if success:
        print("Collection deleted successfully.")

        # Recreate collection with correct dimensions (768 for Cohere embeddings)
        print("Recreating collection with correct dimensions...")
        recreated = qdrant_client.ensure_collection_exists(vector_size=768)

        if recreated:
            print("Collection recreated successfully with 768 dimensions.")
            print(f"Collection '{qdrant_client.collection_name}' is ready for ingestion.")
        else:
            print("Failed to recreate collection.")
    else:
        print("Failed to delete collection.")

    # Check the final state
    count = qdrant_client.count_points()
    print(f"Final vector count in collection: {count}")


if __name__ == "__main__":
    asyncio.run(reset_collection())