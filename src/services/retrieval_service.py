"""
Document retrieval service for semantic search.
"""
from typing import List, Dict, Any, Optional
from src.clients.qdrant_client import QdrantWrapper
from src.clients.cohere_client import CohereWrapper
from src.config.settings import settings
from src.utils.logging import StructuredLogger, log_query_event
import time
import logging


class RetrievalService:
    """
    Service for performing semantic search and document retrieval.
    """

    def __init__(self):
        """Initialize the retrieval service with required clients."""
        self.qdrant_client = QdrantWrapper()
        self.cohere_client = CohereWrapper()
        self.logger = StructuredLogger("retrieval_service")

    async def retrieve_similar_documents(
        self,
        query: str,
        top_k: int = None,
        similarity_threshold: float = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents similar to the query.

        Args:
            query: The query text to find similar documents for
            top_k: Number of documents to retrieve (defaults to settings.TOP_K_RETRIEVAL)
            similarity_threshold: Minimum similarity score threshold (defaults to settings.SIMILARITY_THRESHOLD)
            filters: Optional filters for the search

        Returns:
            List of similar documents with metadata
        """
        start_time = time.time()
        top_k = top_k or settings.TOP_K_RETRIEVAL
        similarity_threshold = similarity_threshold or settings.SIMILARITY_THRESHOLD

        try:
            # Validate input
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")

            if len(query) > settings.MAX_QUERY_LENGTH:
                raise ValueError(f"Query exceeds maximum length of {settings.MAX_QUERY_LENGTH} characters")

            # Implement response time optimization with timeout
            import asyncio
            from src.utils.async_utils import run_with_timeout

            # Generate embedding for the query with timeout
            query_embedding_task = self.cohere_client.embed_query(query)
            query_embedding = await run_with_timeout(query_embedding_task, timeout=10.0)  # 10 second timeout

            # Perform similarity search in Qdrant with configurable threshold
            search_results = self.qdrant_client.search_similar(
                query_vector=query_embedding,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                filters=filters
            )

            # Check if response time is approaching the 3-second target
            elapsed_time = time.time() - start_time
            if elapsed_time > 2.5:  # If we're close to 3 seconds
                self.logger.warning(
                    "Query approaching response time limit",
                    query=query[:100] + "..." if len(query) > 100 else query,
                    elapsed_time=elapsed_time
                )

            # Log the query event
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            log_query_event(
                query=query[:100] + "..." if len(query) > 100 else query,
                result_count=len(search_results),
                response_time_ms=response_time,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )

            return search_results

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(
                "Failed to retrieve similar documents",
                query=query[:100] + "..." if len(query) > 100 else query,
                error=str(e),
                response_time_ms=response_time
            )
            raise

    async def retrieve_by_source_file(self, source_file_path: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve documents specifically from a given source file.

        Args:
            source_file_path: Path of the source file to search within
            top_k: Number of documents to retrieve

        Returns:
            List of documents from the specified source file
        """
        filters = {"source_file_path": source_file_path}
        return await self.retrieve_similar_documents("", top_k=top_k, filters=filters)

    async def retrieve_by_content_keywords(
        self,
        keywords: List[str],
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents matching specific keywords.

        Args:
            keywords: List of keywords to search for
            top_k: Number of documents to retrieve
            similarity_threshold: Minimum similarity score threshold

        Returns:
            List of documents matching the keywords
        """
        # Create a query from keywords
        query = " ".join(keywords)
        return await self.retrieve_similar_documents(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.qdrant_client.count_points()
            model_info = self.cohere_client.get_model_info()

            return {
                "total_documents": count,
                "model_info": model_info,
                "collection_name": settings.COLLECTION_NAME
            }
        except Exception as e:
            self.logger.error("Failed to get collection stats", error=str(e))
            return {}

    async def validate_retrieval(self, query: str, expected_sources: List[str] = None) -> Dict[str, Any]:
        """
        Validate the retrieval functionality by checking results against expected sources.

        Args:
            query: Query to test
            expected_sources: List of expected source files (optional)

        Returns:
            Dictionary with validation results
        """
        try:
            results = await self.retrieve_similar_documents(query, top_k=3)

            validation_result = {
                "query": query,
                "results_count": len(results),
                "sources_found": list(set([result['payload']['source_file_path'] for result in results if 'payload' in result])),
                "scores": [result.get('score', 0) for result in results],
                "valid": True
            }

            if expected_sources:
                found_sources = set(validation_result['sources_found'])
                expected_set = set(expected_sources)
                validation_result['expected_sources_found'] = list(found_sources.intersection(expected_set))
                validation_result['unexpected_sources'] = list(found_sources - expected_set)
                validation_result['all_expected_found'] = expected_set.issubset(found_sources)
                validation_result['valid'] = validation_result['all_expected_found']

            return validation_result

        except Exception as e:
            return {
                "query": query,
                "valid": False,
                "error": str(e)
            }

    async def search_with_hybrid_approach(
        self,
        query: str,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword-based approaches.

        Args:
            query: The query text
            keyword_weight: Weight for keyword-based search (0-1)
            semantic_weight: Weight for semantic search (0-1)
            top_k: Number of results to return

        Returns:
            List of documents with combined scoring
        """
        # This is a simplified hybrid approach - in a real implementation,
        # you might use Qdrant's hybrid search capabilities or implement
        # a more sophisticated combination of scores
        semantic_results = await self.retrieve_similar_documents(query, top_k=top_k * 2)

        # For now, return semantic results with adjusted scores based on weights
        for result in semantic_results:
            result['score'] = result['score'] * semantic_weight

        # Sort by adjusted score and return top_k
        semantic_results.sort(key=lambda x: x['score'], reverse=True)
        return semantic_results[:top_k]

    def health_check(self) -> bool:
        """
        Check if the retrieval service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Check if both clients are working
            qdrant_healthy = self.qdrant_client.health_check()
            # For Cohere, we don't make an actual API call to preserve quota
            # but we could implement a lightweight check if needed

            return qdrant_healthy
        except Exception:
            return False