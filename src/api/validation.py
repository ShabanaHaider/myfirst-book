"""
Input validation for API endpoints in the RAG Chatbot system.
"""
import re
from typing import Dict, Any, List, Optional, Union
from src.config.settings import settings
import logging


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class APIValidator:
    """
    Validator for API inputs with methods for different endpoint types.
    """

    @staticmethod
    def validate_query_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate query endpoint input.

        Args:
            data: Input data for the query endpoint

        Returns:
            Validated and cleaned data

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValidationError("Input must be a JSON object")

        # Validate query
        query = data.get("query", "").strip()
        if not query:
            raise ValidationError("Query is required")

        if len(query) > settings.MAX_QUERY_LENGTH:
            raise ValidationError(f"Query exceeds maximum length of {settings.MAX_QUERY_LENGTH} characters")

        if len(query) < 3:
            raise ValidationError("Query must be at least 3 characters long")

        # Validate top_k
        top_k = data.get("top_k", settings.TOP_K_RETRIEVAL)
        if not isinstance(top_k, int) or top_k <= 0 or top_k > 20:
            raise ValidationError("top_k must be an integer between 1 and 20")

        # Validate similarity_threshold
        similarity_threshold = data.get("similarity_threshold", settings.SIMILARITY_THRESHOLD)
        if not isinstance(similarity_threshold, (int, float)) or similarity_threshold < 0 or similarity_threshold > 1:
            raise ValidationError("similarity_threshold must be a number between 0 and 1")

        # Validate filters (if provided)
        filters = data.get("filters", {})
        if not isinstance(filters, dict):
            raise ValidationError("Filters must be a JSON object")

        # Additional filters validation could be added here

        # Return validated data with defaults applied
        validated_data = {
            "query": query,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "filters": filters
        }

        return validated_data

    @staticmethod
    def validate_ingestion_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate ingestion endpoint input.

        Args:
            data: Input data for the ingestion endpoint

        Returns:
            Validated and cleaned data

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValidationError("Input must be a JSON object")

        # Validate source directory (optional)
        source_dir = data.get("source_directory", settings.DOCS_DIRECTORY)
        if source_dir:
            if not isinstance(source_dir, str):
                raise ValidationError("source_directory must be a string")

            # Basic path validation to prevent directory traversal
            if '..' in source_dir or source_dir.startswith('/'):
                raise ValidationError("Invalid source directory path")

        # Validate file patterns (optional)
        file_patterns = data.get("file_patterns", ["*.md"])
        if not isinstance(file_patterns, list):
            raise ValidationError("file_patterns must be a list of strings")

        for pattern in file_patterns:
            if not isinstance(pattern, str):
                raise ValidationError("Each file pattern must be a string")

        # Validate reprocess flag (optional)
        reprocess = data.get("reprocess", False)
        if not isinstance(reprocess, bool):
            raise ValidationError("reprocess must be a boolean")

        # Validate metadata (optional)
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValidationError("metadata must be a JSON object")

        validated_data = {
            "source_directory": source_dir,
            "file_patterns": file_patterns,
            "reprocess": reprocess,
            "metadata": metadata
        }

        return validated_data

    @staticmethod
    def validate_health_check_input(data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate health check endpoint input.

        Args:
            data: Input data for the health check endpoint (usually None)

        Returns:
            Validated and cleaned data

        Raises:
            ValidationError: If validation fails
        """
        # Health check typically doesn't require input parameters
        if data is not None and not isinstance(data, dict):
            raise ValidationError("Input must be a JSON object or null")

        return data or {}

    @staticmethod
    def validate_config_endpoint_input(data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate configuration endpoint input.

        Args:
            data: Input data for the configuration endpoint (usually None)

        Returns:
            Validated and cleaned data

        Raises:
            ValidationError: If validation fails
        """
        # Config endpoint typically doesn't require input parameters
        if data is not None and not isinstance(data, dict):
            raise ValidationError("Input must be a JSON object or null")

        return data or {}

    @staticmethod
    def validate_text_content(text: str, field_name: str = "content", max_length: Optional[int] = None) -> str:
        """
        Validate general text content.

        Args:
            text: Text to validate
            field_name: Name of the field for error messages
            max_length: Maximum allowed length (optional)

        Returns:
            Validated and cleaned text

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(text, str):
            raise ValidationError(f"{field_name} must be a string")

        text = text.strip()
        if not text:
            raise ValidationError(f"{field_name} cannot be empty")

        if max_length and len(text) > max_length:
            raise ValidationError(f"{field_name} exceeds maximum length of {max_length} characters")

        # Check for potentially dangerous content (basic injection prevention)
        dangerous_patterns = [
            r'<script',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'vbscript:',  # VBScript URLs
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValidationError(f"{field_name} contains potentially dangerous content")

        return text

    @staticmethod
    def validate_file_path(file_path: str) -> str:
        """
        Validate file path to prevent directory traversal.

        Args:
            file_path: File path to validate

        Returns:
            Validated and cleaned file path

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(file_path, str):
            raise ValidationError("File path must be a string")

        # Remove leading/trailing whitespace
        file_path = file_path.strip()

        if not file_path:
            raise ValidationError("File path cannot be empty")

        # Prevent directory traversal
        if '..' in file_path:
            raise ValidationError("File path contains invalid directory traversal")

        # Prevent absolute paths (basic check)
        if file_path.startswith(('/', '\\')):
            raise ValidationError("File path cannot be absolute")

        return file_path

    @staticmethod
    def validate_number_range(value: Union[int, float], min_val: Union[int, float],
                            max_val: Union[int, float], field_name: str = "value") -> Union[int, float]:
        """
        Validate that a number is within a specified range.

        Args:
            value: Number to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            field_name: Name of the field for error messages

        Returns:
            Validated number

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(f"{field_name} must be a number")

        if value < min_val or value > max_val:
            raise ValidationError(f"{field_name} must be between {min_val} and {max_val}")

        return value

    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitize query string to prevent injection attacks.

        Args:
            query: Query string to sanitize

        Returns:
            Sanitized query string
        """
        # Remove potentially dangerous characters/sequences
        # This is a basic sanitization - in production, use more comprehensive methods
        sanitized = re.sub(r'[<>"\';]', '', query)
        return sanitized.strip()

    @staticmethod
    def validate_document_chunk(chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate document chunk data.

        Args:
            chunk_data: Document chunk data to validate

        Returns:
            Validated document chunk data

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(chunk_data, dict):
            raise ValidationError("Document chunk must be a JSON object")

        # Validate required fields
        required_fields = ["content", "source_file_path"]
        for field in required_fields:
            if field not in chunk_data:
                raise ValidationError(f"Missing required field: {field}")

        # Validate content
        content = APIValidator.validate_text_content(
            chunk_data["content"],
            "content",
            max_length=10000  # Reasonable limit for a chunk
        )

        # Validate source file path
        source_file_path = APIValidator.validate_file_path(chunk_data["source_file_path"])

        # Validate optional fields
        chunk_index = chunk_data.get("chunk_index", 0)
        if not isinstance(chunk_index, int) or chunk_index < 0:
            raise ValidationError("chunk_index must be a non-negative integer")

        character_position = chunk_data.get("character_position", 0)
        if not isinstance(character_position, int) or character_position < 0:
            raise ValidationError("character_position must be a non-negative integer")

        validated_chunk = {
            "content": content,
            "source_file_path": source_file_path,
            "chunk_index": chunk_index,
            "character_position": character_position
        }

        # Add optional fields if present and valid
        if "content_hash" in chunk_data:
            content_hash = chunk_data["content_hash"]
            if not isinstance(content_hash, str) or len(content_hash) != 64:  # SHA-256 hash length
                raise ValidationError("content_hash must be a valid SHA-256 hash string (64 characters)")
            validated_chunk["content_hash"] = content_hash

        if "chunk_size_tokens" in chunk_data:
            chunk_size_tokens = chunk_data["chunk_size_tokens"]
            if not isinstance(chunk_size_tokens, int) or chunk_size_tokens <= 0:
                raise ValidationError("chunk_size_tokens must be a positive integer")
            validated_chunk["chunk_size_tokens"] = chunk_size_tokens

        return validated_chunk


def validate_api_input(endpoint_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate API input based on endpoint type.

    Args:
        endpoint_type: Type of endpoint ('query', 'ingestion', 'health', 'config')
        data: Input data to validate

    Returns:
        Validated data

    Raises:
        ValidationError: If validation fails
    """
    validator = APIValidator()

    if endpoint_type == "query":
        return validator.validate_query_input(data)
    elif endpoint_type == "ingestion":
        return validator.validate_ingestion_input(data)
    elif endpoint_type == "health":
        return validator.validate_health_check_input(data)
    elif endpoint_type == "config":
        return validator.validate_config_endpoint_input(data)
    else:
        raise ValidationError(f"Unknown endpoint type: {endpoint_type}")


# Convenience functions for each endpoint type
def validate_query_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate query endpoint data."""
    return APIValidator.validate_query_input(data)


def validate_ingestion_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate ingestion endpoint data."""
    return APIValidator.validate_ingestion_input(data)


def validate_health_data(data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate health check endpoint data."""
    return APIValidator.validate_health_check_input(data)


def validate_config_data(data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate configuration endpoint data."""
    return APIValidator.validate_config_endpoint_input(data)