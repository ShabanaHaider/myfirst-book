"""
Error responses and handling for API endpoints in the RAG Chatbot system.
"""
from typing import Dict, Any, Optional
from enum import Enum
import logging
from src.utils.logging import get_logger


class ErrorCode(Enum):
    """Enumeration of API error codes."""
    # General errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Specific RAG errors
    QUERY_TOO_SHORT = "QUERY_TOO_SHORT"
    QUERY_TOO_LONG = "QUERY_TOO_LONG"
    EMBEDDING_GENERATION_FAILED = "EMBEDDING_GENERATION_FAILED"
    VECTOR_STORAGE_FAILED = "VECTOR_STORAGE_FAILED"
    RETRIEVAL_FAILED = "RETRIEVAL_FAILED"
    COHERE_API_ERROR = "COHERE_API_ERROR"
    QDRANT_CONNECTION_ERROR = "QDRANT_CONNECTION_ERROR"
    DOCUMENT_PROCESSING_ERROR = "DOCUMENT_PROCESSING_ERROR"
    CONFIG_VALIDATION_ERROR = "CONFIG_VALIDATION_ERROR"


class APIError(Exception):
    """Custom API error with code and details."""

    def __init__(self, message: str, error_code: ErrorCode, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = self._get_timestamp()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary for JSON response."""
        return {
            "error": {
                "code": self.error_code.value,
                "message": self.message,
                "status_code": self.status_code,
                "timestamp": self.timestamp,
                "details": self.details
            }
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


class APIErrorHandler:
    """Handler for API errors with consistent response format."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle an error and return a consistent error response.

        Args:
            error: The exception to handle
            context: Additional context about where the error occurred

        Returns:
            Dictionary with error response
        """
        if isinstance(error, APIError):
            # If it's already an APIError, log and return as is
            self.logger.error(f"API Error in {context}: {error.message}", extra={
                "error_code": error.error_code.value,
                "status_code": error.status_code,
                "details": error.details
            })
            return error.to_dict()

        elif isinstance(error, ValueError):
            # Handle validation errors
            api_error = APIError(
                message=str(error),
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400
            )
            self.logger.error(f"Validation Error in {context}: {str(error)}")
            return api_error.to_dict()

        elif isinstance(error, FileNotFoundError):
            # Handle file not found errors
            api_error = APIError(
                message="Requested file or resource not found",
                error_code=ErrorCode.NOT_FOUND,
                status_code=404,
                details={"path": str(error)}
            )
            self.logger.error(f"File Not Found Error in {context}: {str(error)}")
            return api_error.to_dict()

        else:
            # Handle unexpected errors
            api_error = APIError(
                message="An internal error occurred",
                error_code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                details={"original_error": str(type(error).__name__), "context": context}
            )
            self.logger.error(f"Unexpected Error in {context}: {str(error)}", exc_info=True)
            return api_error.to_dict()

    def create_error_response(self, error_code: ErrorCode, message: str,
                            status_code: int = 500, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a standardized error response.

        Args:
            error_code: The error code
            message: Error message
            status_code: HTTP status code
            details: Additional error details

        Returns:
            Dictionary with error response
        """
        error = APIError(message, error_code, status_code, details)
        self.logger.error(f"Error Response Created: {message}", extra={
            "error_code": error_code.value,
            "status_code": status_code
        })
        return error.to_dict()

    def handle_validation_error(self, field: str, value: Any, expected_type: str = None) -> Dict[str, Any]:
        """Handle validation errors specifically."""
        message = f"Invalid value for field '{field}'"
        if expected_type:
            message += f". Expected {expected_type}, got {type(value).__name__}"

        api_error = APIError(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"field": field, "value": value, "expected_type": expected_type}
        )
        self.logger.error(f"Validation Error: {message}")
        return api_error.to_dict()

    def handle_embedding_error(self, original_error: Exception) -> Dict[str, Any]:
        """Handle embedding-related errors."""
        api_error = APIError(
            message="Failed to generate embeddings",
            error_code=ErrorCode.EMBEDDING_GENERATION_FAILED,
            status_code=500,
            details={"original_error": str(original_error)}
        )
        self.logger.error(f"Embedding Error: {str(original_error)}", exc_info=True)
        return api_error.to_dict()

    def handle_storage_error(self, original_error: Exception) -> Dict[str, Any]:
        """Handle vector storage errors."""
        api_error = APIError(
            message="Failed to store vectors in Qdrant",
            error_code=ErrorCode.VECTOR_STORAGE_FAILED,
            status_code=500,
            details={"original_error": str(original_error)}
        )
        self.logger.error(f"Storage Error: {str(original_error)}", exc_info=True)
        return api_error.to_dict()

    def handle_retrieval_error(self, original_error: Exception) -> Dict[str, Any]:
        """Handle retrieval errors."""
        api_error = APIError(
            message="Failed to retrieve similar documents",
            error_code=ErrorCode.RETRIEVAL_FAILED,
            status_code=500,
            details={"original_error": str(original_error)}
        )
        self.logger.error(f"Retrieval Error: {str(original_error)}", exc_info=True)
        return api_error.to_dict()

    def handle_cohere_error(self, original_error: Exception) -> Dict[str, Any]:
        """Handle Cohere API errors."""
        api_error = APIError(
            message="Cohere API request failed",
            error_code=ErrorCode.COHERE_API_ERROR,
            status_code=502,  # Bad Gateway for external API errors
            details={"original_error": str(original_error)}
        )
        self.logger.error(f"Cohere API Error: {str(original_error)}", exc_info=True)
        return api_error.to_dict()

    def handle_qdrant_error(self, original_error: Exception) -> Dict[str, Any]:
        """Handle Qdrant connection errors."""
        api_error = APIError(
            message="Qdrant database connection failed",
            error_code=ErrorCode.QDRANT_CONNECTION_ERROR,
            status_code=502,  # Bad Gateway for external service errors
            details={"original_error": str(original_error)}
        )
        self.logger.error(f"Qdrant Connection Error: {str(original_error)}", exc_info=True)
        return api_error.to_dict()


# Global error handler instance
error_handler = APIErrorHandler()


def handle_api_error(error: Exception, context: str = "") -> Dict[str, Any]:
    """
    Convenience function to handle API errors using the global handler.

    Args:
        error: The exception to handle
        context: Additional context about where the error occurred

    Returns:
        Dictionary with error response
    """
    return error_handler.handle_error(error, context)


def create_error_response(error_code: ErrorCode, message: str,
                         status_code: int = 500, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to create error responses using the global handler.

    Args:
        error_code: The error code
        message: Error message
        status_code: HTTP status code
        details: Additional error details

    Returns:
        Dictionary with error response
    """
    return error_handler.create_error_response(error_code, message, status_code, details)


def handle_validation_error(field: str, value: Any, expected_type: str = None) -> Dict[str, Any]:
    """Convenience function for validation errors."""
    return error_handler.handle_validation_error(field, value, expected_type)


def handle_embedding_error(original_error: Exception) -> Dict[str, Any]:
    """Convenience function for embedding errors."""
    return error_handler.handle_embedding_error(original_error)


def handle_storage_error(original_error: Exception) -> Dict[str, Any]:
    """Convenience function for storage errors."""
    return error_handler.handle_storage_error(original_error)


def handle_retrieval_error(original_error: Exception) -> Dict[str, Any]:
    """Convenience function for retrieval errors."""
    return error_handler.handle_retrieval_error(original_error)


def handle_cohere_error(original_error: Exception) -> Dict[str, Any]:
    """Convenience function for Cohere errors."""
    return error_handler.handle_cohere_error(original_error)


def handle_qdrant_error(original_error: Exception) -> Dict[str, Any]:
    """Convenience function for Qdrant errors."""
    return error_handler.handle_qdrant_error(original_error)


# Standard error responses for common scenarios
STANDARD_ERRORS = {
    "not_found": lambda resource: create_error_response(
        ErrorCode.NOT_FOUND,
        f"{resource} not found",
        404
    ),
    "unauthorized": lambda: create_error_response(
        ErrorCode.UNAUTHORIZED,
        "Unauthorized access",
        401
    ),
    "rate_limit": lambda: create_error_response(
        ErrorCode.RATE_LIMIT_EXCEEDED,
        "Rate limit exceeded",
        429
    ),
    "internal_error": lambda: create_error_response(
        ErrorCode.INTERNAL_ERROR,
        "Internal server error",
        500
    ),
    "validation_error": lambda details: create_error_response(
        ErrorCode.VALIDATION_ERROR,
        "Validation failed",
        400,
        details
    )
}


def get_standard_error(error_type: str, *args) -> Dict[str, Any]:
    """
    Get a standard error response.

    Args:
        error_type: Type of standard error ('not_found', 'unauthorized', etc.)
        *args: Arguments to pass to the error function

    Returns:
        Dictionary with error response
    """
    if error_type in STANDARD_ERRORS:
        return STANDARD_ERRORS[error_type](*args)
    else:
        return STANDARD_ERRORS["internal_error"]()