"""
Qdrant client wrapper with connection management.
"""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    PointStruct,
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType
)
from src.config.settings import settings
from src.models.embedding_vector import EmbeddingVector
import logging


class QdrantWrapper:
    """
    A wrapper around the Qdrant client with connection management and convenience methods.
    """

    def __init__(self):
        """Initialize the Qdrant client with connection settings."""
        self.client = None
        self.collection_name = settings.COLLECTION_NAME
        self._connect()

    def _connect(self):
        """Establish connection to Qdrant."""
        try:
            if settings.QDRANT_URL:
                # Use URL if provided (for Qdrant Cloud)
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                    prefer_grpc=True
                )
            else:
                # Use host/port for local Qdrant
                self.client = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    api_key=settings.QDRANT_API_KEY
                )
            logging.info("Successfully connected to Qdrant")
        except Exception as e:
            logging.error(f"Failed to connect to Qdrant: {e}")
            raise

    def ensure_collection_exists(self, vector_size: int = 768) -> bool:
        """
        Ensure the collection exists with proper configuration.

        Args:
            vector_size: Size of the embedding vectors (default 768 for Cohere multilingual model)

        Returns:
            True if collection exists or was created successfully
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection with appropriate vector size
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logging.info(f"Created Qdrant collection: {self.collection_name}")

                # Create payload index for source_file_path to optimize filtering
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="source_file_path",
                    field_schema=PayloadSchemaType.KEYWORD
                )
            else:
                logging.info(f"Qdrant collection already exists: {self.collection_name}")

            return True
        except Exception as e:
            logging.error(f"Failed to ensure collection exists: {e}")
            return False

    def upsert_embedding(self, embedding_vector: EmbeddingVector) -> bool:
        """
        Upsert a single embedding vector into Qdrant.

        Args:
            embedding_vector: The embedding vector to store

        Returns:
            True if successful
        """
        try:
            points = [PointStruct(
                id=embedding_vector.id,
                vector=embedding_vector.vector,
                payload=embedding_vector.metadata
            )]

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            return True
        except Exception as e:
            logging.error(f"Failed to upsert embedding: {e}")
            return False

    def upsert_embeddings_batch(self, embedding_vectors: List[EmbeddingVector]) -> bool:
        """
        Upsert multiple embedding vectors into Qdrant in a batch operation.

        Args:
            embedding_vectors: List of embedding vectors to store

        Returns:
            True if successful
        """
        try:
            points = []
            for embedding_vector in embedding_vectors:
                point = PointStruct(
                    id=embedding_vector.id,
                    vector=embedding_vector.vector,
                    payload=embedding_vector.metadata
                )
                points.append(point)

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logging.info(f"Upserted {len(embedding_vectors)} embeddings to Qdrant")
            return True
        except Exception as e:
            logging.error(f"Failed to upsert embeddings batch: {e}")
            return False

    def search_similar(self, query_vector: List[float], top_k: int = 5,
                      similarity_threshold: float = 0.7,
                      filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in Qdrant.

        Args:
            query_vector: The query embedding vector
            top_k: Number of similar vectors to return
            similarity_threshold: Minimum similarity score threshold
            filters: Optional filters for the search

        Returns:
            List of similar vectors with metadata
        """
        try:
            # Build filter conditions if provided
            qdrant_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )

                if conditions:
                    qdrant_filter = Filter(must=conditions)

            # Use the modern Qdrant API (query_points method) - this is what's available in version 1.9.1
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=top_k,
                score_threshold=similarity_threshold,
                with_payload=True,  # Explicitly request payload
                with_vectors=False  # We don't need the vectors back, just payload and score
            )

            # Format results to include both payload and score
            # The query_points method returns a QueryResponse object with a 'points' attribute
            formatted_results = []
            for scored_point in results.points:  # Access the points from the QueryResponse
                formatted_results.append({
                    'id': scored_point.id,
                    'score': scored_point.score,
                    'payload': scored_point.payload if hasattr(scored_point, 'payload') else {}
                })

            return formatted_results
        except AttributeError as e:
            # Handle case where query_points method doesn't exist (fallback to search)
            logging.error(f"Query points method not found on QdrantClient: {e}")
            logging.error("Available methods: " + str([method for method in dir(self.client) if not method.startswith('_')]))

            # Fallback to the older search API if query_points doesn't exist
            search_params = {
                'collection_name': self.collection_name,
                'query_vector': query_vector,
                'query_filter': qdrant_filter,
                'limit': top_k,
                'score_threshold': similarity_threshold,
                'with_payload': True,  # Explicitly request payload
                'with_vectors': False  # We don't need the vectors back, just payload and score
            }

            try:
                results = self.client.search(**search_params)

                # Format results for the older API
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        'id': result.id,
                        'score': result.score,
                        'payload': result.payload if hasattr(result, 'payload') else {}
                    })

                return formatted_results
            except (TypeError, AttributeError):
                # If with_payload/with_vectors parameters are not accepted, try without them
                search_params.pop('with_payload')
                search_params.pop('with_vectors')
                results = self.client.search(**search_params)

                # Format results for the older API
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        'id': result.id,
                        'score': result.score,
                        'payload': getattr(result, 'payload', {})
                    })

                return formatted_results
        except Exception as e:
            logging.error(f"Search failed: {e}")
            return []

    def get_embedding_by_id(self, embedding_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single embedding by its ID.

        Args:
            embedding_id: The ID of the embedding to retrieve

        Returns:
            Embedding data if found, None otherwise
        """
        try:
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[embedding_id]
            )

            if results:
                result = results[0]
                return {
                    'id': result.id,
                    'vector': result.vector,
                    'payload': result.payload
                }
            return None
        except Exception as e:
            logging.error(f"Failed to retrieve embedding by ID: {e}")
            return None

    def delete_embedding_by_id(self, embedding_id: str) -> bool:
        """
        Delete an embedding by its ID.

        Args:
            embedding_id: The ID of the embedding to delete

        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[embedding_id]
            )
            return True
        except Exception as e:
            logging.error(f"Failed to delete embedding: {e}")
            return False

    def delete_by_payload(self, key: str, value: Any) -> bool:
        """
        Delete embeddings that match a specific payload condition.

        Args:
            key: The payload key to match
            value: The value to match

        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    ]
                )
            )
            return True
        except Exception as e:
            logging.error(f"Failed to delete embeddings by payload: {e}")
            return False

    def count_points(self) -> int:
        """
        Count the total number of points in the collection.

        Returns:
            Total number of points in the collection
        """
        try:
            count = self.client.count(
                collection_name=self.collection_name
            )
            return count.count
        except Exception as e:
            logging.error(f"Failed to count points: {e}")
            return 0

    def delete_collection(self) -> bool:
        """
        Delete the current collection if it exists.

        Returns:
            True if successful or if collection doesn't exist
        """
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name in collection_names:
                self.client.delete_collection(collection_name=self.collection_name)
                logging.info(f"Deleted Qdrant collection: {self.collection_name}")
                return True
            else:
                logging.info(f"Collection does not exist, no need to delete: {self.collection_name}")
                return True
        except Exception as e:
            logging.error(f"Failed to delete collection: {e}")
            return False

    def health_check(self) -> bool:
        """
        Check if Qdrant is accessible and healthy.

        Returns:
            True if Qdrant is accessible
        """
        try:
            # Try to get collections as a basic health check
            self.client.get_collections()
            return True
        except Exception:
            return False