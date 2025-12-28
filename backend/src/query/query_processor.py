"""
Query processing module for embedding user queries.
"""
from typing import List, Dict, Any
import logging
from src.clients.cohere_client import CohereWrapper
from src.utils.text_utils import clean_text, normalize_whitespace
from src.utils.logging import StructuredLogger
from src.exceptions import QueryError, ValidationError


class QueryProcessor:
    """
    Module for processing user queries and converting them to embeddings.
    """

    def __init__(self):
        """Initialize the query processor with required clients."""
        self.cohere_client = CohereWrapper()
        self.logger = StructuredLogger("query_processor")

    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query and prepare it for retrieval.

        Args:
            query: The raw user query

        Returns:
            Dictionary with processed query and embedding
        """
        try:
            # Validate input
            if not query or not query.strip():
                raise ValidationError("Query cannot be empty")

            # Clean and normalize the query
            cleaned_query = self.preprocess_query(query)

            # Validate query length
            if len(cleaned_query) > 1000:  # Arbitrary limit, can be configured
                raise ValidationError("Query is too long")

            # Generate embedding for the query
            query_embedding = await self.cohere_client.embed_query(cleaned_query)

            # Validate embedding dimensions
            if not self.cohere_client.validate_embeddings([query_embedding]):
                raise QueryError("Invalid embedding generated for query")

            return {
                "original_query": query,
                "processed_query": cleaned_query,
                "embedding": query_embedding,
                "query_length": len(cleaned_query)
            }

        except ValidationError as e:
            self.logger.error("Query validation failed", query=query, error=str(e))
            raise
        except Exception as e:
            self.logger.error("Query processing failed", query=query, error=str(e))
            raise QueryError(f"Failed to process query: {str(e)}")

    def preprocess_query(self, query: str) -> str:
        """
        Preprocess the query by cleaning and normalizing.

        Args:
            query: The raw query string

        Returns:
            Cleaned and normalized query string
        """
        # Clean extra whitespace
        query = clean_text(query)
        # Normalize whitespace
        query = normalize_whitespace(query)
        return query.strip()

    async def batch_process_queries(self, queries: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple queries in a batch.

        Args:
            queries: List of query strings

        Returns:
            List of processed query results
        """
        results = []
        for query in queries:
            try:
                result = await self.process_query(query)
                results.append(result)
            except Exception as e:
                # Log the error but continue processing other queries
                self.logger.error("Failed to process query in batch", query=query, error=str(e))
                results.append({
                    "original_query": query,
                    "error": str(e),
                    "success": False
                })

        return results

    async def validate_query_quality(self, query: str) -> Dict[str, Any]:
        """
        Validate the quality of a query for retrieval purposes.

        Args:
            query: The query to validate

        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "query": query,
            "is_valid": True,
            "issues": [],
            "suggestions": []
        }

        # Check if query is too short
        if len(query.strip()) < 3:
            validation_result["is_valid"] = False
            validation_result["issues"].append("Query is too short")
            validation_result["suggestions"].append("Make your query more specific")

        # Check if query contains only special characters
        if query.strip() and not any(c.isalnum() for c in query):
            validation_result["is_valid"] = False
            validation_result["issues"].append("Query contains no alphanumeric characters")
            validation_result["suggestions"].append("Include meaningful words in your query")

        # Check query length
        if len(query) > 500:
            validation_result["is_valid"] = False
            validation_result["issues"].append("Query is too long")
            validation_result["suggestions"].append("Shorten your query to be more specific")

        return validation_result

    async def expand_query(self, query: str) -> List[str]:
        """
        Expand a query with related terms (simple implementation).

        Args:
            query: The original query

        Returns:
            List of expanded query terms
        """
        # For now, return the original query and individual words
        # In a more sophisticated implementation, you might use
        # semantic expansion, synonyms, or related terms from embeddings
        words = query.split()
        expanded_terms = [query]  # Original query
        expanded_terms.extend(words)  # Individual words

        # Remove duplicates while preserving order
        unique_terms = list(dict.fromkeys(expanded_terms))
        return unique_terms

    async def extract_query_entities(self, query: str) -> List[str]:
        """
        Extract key entities from the query (simple keyword extraction).

        Args:
            query: The query to extract entities from

        Returns:
            List of extracted entities/keywords
        """
        # Simple approach: split by spaces and filter out common stop words
        # In a real implementation, you might use NLP techniques
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }

        words = query.lower().split()
        entities = [word for word in words if word.lower() not in stop_words and len(word) > 2]
        return entities

    async def get_query_embedding_with_metadata(self, query: str) -> Dict[str, Any]:
        """
        Get query embedding with additional metadata.

        Args:
            query: The query to embed

        Returns:
            Dictionary with embedding and metadata
        """
        processed = await self.process_query(query)

        return {
            "embedding": processed["embedding"],
            "metadata": {
                "original_query": processed["original_query"],
                "processed_query": processed["processed_query"],
                "query_length": processed["query_length"],
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "model_used": self.cohere_client.model
            }
        }

    def health_check(self) -> bool:
        """
        Check if the query processor is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Check if Cohere client is accessible
            model_info = self.cohere_client.get_model_info()
            return bool(model_info)
        except Exception:
            return False