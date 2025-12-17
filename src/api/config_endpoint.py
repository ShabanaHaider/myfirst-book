"""
Configuration endpoint for the RAG Chatbot system.
"""
from typing import Dict, Any, List
from src.config.settings import settings
from src.clients.qdrant_client import QdrantWrapper
from src.clients.cohere_client import CohereWrapper
import time
import logging


class ConfigService:
    """
    Service for managing and exposing system configuration.
    """

    def __init__(self):
        """Initialize the config service."""
        self.qdrant_client = QdrantWrapper()
        self.cohere_client = CohereWrapper()

    def get_system_config(self) -> Dict[str, Any]:
        """
        Get the current system configuration.

        Returns:
            Dictionary with system configuration details
        """
        config_data = {
            "processing_parameters": {
                "chunk_size_tokens": settings.CHUNK_SIZE_TOKENS,
                "overlap_percentage": settings.OVERLAP_PERCENTAGE,
                "top_k_retrieval": settings.TOP_K_RETRIEVAL,
                "similarity_threshold": settings.SIMILARITY_THRESHOLD,
                "max_query_length": settings.MAX_QUERY_LENGTH,
                "collection_name": settings.COLLECTION_NAME
            },
            "performance_limits": {
                "batch_size": settings.BATCH_SIZE,
                "max_concurrent_requests": settings.MAX_CONCURRENT_REQUESTS,
                "response_timeout_seconds": settings.RESPONSE_TIMEOUT_SECONDS
            },
            "file_paths": {
                "docs_directory": settings.DOCS_DIRECTORY,
                "processed_chunks_dir": settings.PROCESSED_CHUNKS_DIR
            },
            "qdrant_config": {
                "qdrant_url": settings.QDRANT_URL if settings.QDRANT_URL else "Not set (using host/port)",
                "qdrant_host": settings.QDRANT_HOST,
                "qdrant_port": settings.QDRANT_PORT,
                "collection_exists": self._check_collection_exists()
            },
            "cohere_config": {
                "model_info": self.cohere_client.get_model_info()
            },
            "system_info": {
                "timestamp": time.time(),
                "server_time": time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime()),
                "batch_size": settings.BATCH_SIZE
            }
        }

        return config_data

    def get_sensitive_config(self) -> Dict[str, Any]:
        """
        Get sensitive configuration details (only when needed for debugging).

        Returns:
            Dictionary with sensitive configuration details
        """
        config_data = {
            "api_keys_set": {
                "cohere_api_key_set": bool(settings.COHERE_API_KEY),
                "qdrant_api_key_set": bool(settings.QDRANT_API_KEY)
            },
            "qdrant_config": {
                "qdrant_url": settings.QDRANT_URL,
                "qdrant_api_key": "Set" if settings.QDRANT_API_KEY else "Not set",
                "qdrant_host": settings.QDRANT_HOST,
                "qdrant_port": settings.QDRANT_PORT
            }
        }

        return config_data

    def get_config_validation_report(self) -> Dict[str, Any]:
        """
        Get a validation report for the current configuration.

        Returns:
            Dictionary with validation results
        """
        validation_errors = settings.validate()
        is_valid = len(validation_errors) == 0

        validation_report = {
            "is_valid": is_valid,
            "validation_errors": validation_errors,
            "configured_components": {
                "qdrant_accessible": self.qdrant_client.health_check(),
                "cohere_accessible": self._check_cohere_accessible()
            }
        }

        return validation_report

    def _check_collection_exists(self) -> bool:
        """
        Check if the Qdrant collection exists.

        Returns:
            True if collection exists, False otherwise
        """
        try:
            # Try to get collections to check if the service is accessible
            collections = self.qdrant_client.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            return settings.COLLECTION_NAME in collection_names
        except Exception as e:
            logging.error(f"Error checking collection existence: {e}")
            return False

    def _check_cohere_accessible(self) -> bool:
        """
        Check if Cohere API is accessible.

        Returns:
            True if Cohere is accessible, False otherwise
        """
        try:
            # Try to get model info as a basic check
            model_info = self.cohere_client.get_model_info()
            return bool(model_info)
        except Exception:
            return False


def create_config_endpoint() -> Dict[str, Any]:
    """
    Create a configuration endpoint response.

    Returns:
        Dictionary with configuration details
    """
    config_service = ConfigService()
    return config_service.get_system_config()


def get_config_details() -> Dict[str, Any]:
    """
    Get detailed configuration information.

    Returns:
        Dictionary with detailed configuration
    """
    config_service = ConfigService()
    return {
        "system_config": config_service.get_system_config(),
        "validation_report": config_service.get_config_validation_report()
    }


def get_public_config() -> Dict[str, Any]:
    """
    Get public-facing configuration (without sensitive details).

    Returns:
        Dictionary with public configuration
    """
    config_service = ConfigService()
    system_config = config_service.get_system_config()

    # Remove any potentially sensitive information
    public_config = {
        "processing_parameters": system_config["processing_parameters"],
        "performance_limits": system_config["performance_limits"],
        "file_paths": system_config["file_paths"],
        "qdrant_config": {
            "collection_exists": system_config["qdrant_config"]["collection_exists"]
        },
        "cohere_config": {
            "model_info": system_config["cohere_config"]["model_info"]
        },
        "system_info": system_config["system_info"]
    }

    return public_config