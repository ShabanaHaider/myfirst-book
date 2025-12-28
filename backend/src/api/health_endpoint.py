"""
Health check endpoint for the RAG Chatbot system.
"""
from typing import Dict, Any, Callable
from src.clients.qdrant_client import QdrantWrapper
from src.clients.cohere_client import CohereWrapper
from src.config.settings import settings
import time
import logging


class HealthCheckService:
    """
    Service for performing health checks on the RAG Chatbot system.
    """

    def __init__(self):
        """Initialize the health check service with required clients."""
        self.qdrant_client = QdrantWrapper()
        self.cohere_client = CohereWrapper()

    def check_system_health(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check of the system.

        Returns:
            Dictionary with health check results
        """
        start_time = time.time()

        # Check each component
        qdrant_healthy = self.qdrant_client.health_check()
        cohere_healthy = self._check_cohere_health()
        config_valid = self._check_config_validity()

        total_time = time.time() - start_time

        health_result = {
            "status": "healthy" if all([qdrant_healthy, cohere_healthy, config_valid]) else "unhealthy",
            "timestamp": time.time(),
            "response_time_ms": round(total_time * 1000, 2),
            "components": {
                "qdrant": {
                    "status": "healthy" if qdrant_healthy else "unhealthy",
                    "details": "Qdrant connection is accessible"
                },
                "cohere": {
                    "status": "healthy" if cohere_healthy else "unhealthy",
                    "details": "Cohere API key is valid and accessible"
                },
                "config": {
                    "status": "healthy" if config_valid else "unhealthy",
                    "details": "Configuration is valid"
                }
            },
            "collection_stats": self._get_collection_stats() if qdrant_healthy else None
        }

        return health_result

    def _check_cohere_health(self) -> bool:
        """
        Check if Cohere API is accessible and functional.

        Returns:
            True if Cohere is healthy, False otherwise
        """
        try:
            # Try to get model info as a basic health check
            model_info = self.cohere_client.get_model_info()
            return bool(model_info and "model" in model_info)
        except Exception as e:
            logging.error(f"Cohere health check failed: {e}")
            return False

    def _check_config_validity(self) -> bool:
        """
        Check if the system configuration is valid.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            validation_errors = settings.validate()
            return len(validation_errors) == 0
        except Exception as e:
            logging.error(f"Configuration validation failed: {e}")
            return False

    def _get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Qdrant collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.qdrant_client.count_points()
            return {
                "total_points": count,
                "collection_name": self.qdrant_client.collection_name
            }
        except Exception as e:
            logging.error(f"Failed to get collection stats: {e}")
            return {
                "total_points": 0,
                "collection_name": self.qdrant_client.collection_name,
                "error": str(e)
            }


# FastAPI-style endpoint function
def create_health_endpoint() -> Callable:
    """
    Create a health check endpoint function.

    Returns:
        Function that returns health check results
    """
    health_service = HealthCheckService()

    def health_check():
        return health_service.check_system_health()

    return health_check


# For direct usage without FastAPI
def get_health_status() -> Dict[str, Any]:
    """
    Get the current health status of the system.

    Returns:
        Dictionary with health status
    """
    health_service = HealthCheckService()
    return health_service.check_system_health()