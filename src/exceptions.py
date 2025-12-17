"""
Custom exceptions for the RAG Chatbot system.
"""


class RAGBaseException(Exception):
    """
    Base exception class for all RAG Chatbot exceptions.
    """
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}

    def __str__(self):
        return f"[{self.error_code}] {self.message}"

    def to_dict(self) -> dict:
        """
        Convert the exception to a dictionary for structured logging.

        Returns:
            Dictionary representation of the exception
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ConfigurationError(RAGBaseException):
    """
    Raised when there's an issue with application configuration.
    """
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "CONFIG_ERROR", details)


class DocumentProcessingError(RAGBaseException):
    """
    Raised when there's an issue processing a document.
    """
    def __init__(self, message: str, file_path: str = None, details: dict = None):
        details = details or {}
        if file_path:
            details["file_path"] = file_path
        super().__init__(message, "DOCUMENT_PROCESSING_ERROR", details)


class EmbeddingError(RAGBaseException):
    """
    Raised when there's an issue with embedding generation.
    """
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "EMBEDDING_ERROR", details)


class VectorDatabaseError(RAGBaseException):
    """
    Raised when there's an issue with vector database operations.
    """
    def __init__(self, message: str, operation: str = None, details: dict = None):
        details = details or {}
        if operation:
            details["operation"] = operation
        super().__init__(message, "VECTOR_DATABASE_ERROR", details)


class QueryError(RAGBaseException):
    """
    Raised when there's an issue with query processing.
    """
    def __init__(self, message: str, query: str = None, details: dict = None):
        details = details or {}
        if query:
            details["query"] = query
        super().__init__(message, "QUERY_ERROR", details)


class APIError(RAGBaseException):
    """
    Raised when there's an issue with external API calls.
    """
    def __init__(self, message: str, api_name: str = None, status_code: int = None, details: dict = None):
        details = details or {}
        if api_name:
            details["api_name"] = api_name
        if status_code is not None:
            details["status_code"] = status_code
        super().__init__(message, "API_ERROR", details)


class RateLimitError(APIError):
    """
    Raised when API rate limits are exceeded.
    """
    def __init__(self, message: str = "API rate limit exceeded", api_name: str = None, details: dict = None):
        details = details or {}
        details["retry_after"] = details.get("retry_after", 60)  # Default retry after 60 seconds
        super().__init__(message, api_name, 429, details)


class ValidationError(RAGBaseException):
    """
    Raised when validation fails.
    """
    def __init__(self, message: str, field: str = None, value: str = None, details: dict = None):
        details = details or {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        super().__init__(message, "VALIDATION_ERROR", details)


class FileOperationError(RAGBaseException):
    """
    Raised when there's an issue with file operations.
    """
    def __init__(self, message: str, file_path: str = None, operation: str = None, details: dict = None):
        details = details or {}
        if file_path:
            details["file_path"] = file_path
        if operation:
            details["operation"] = operation
        super().__init__(message, "FILE_OPERATION_ERROR", details)


class CacheError(RAGBaseException):
    """
    Raised when there's an issue with caching operations.
    """
    def __init__(self, message: str, cache_key: str = None, details: dict = None):
        details = details or {}
        if cache_key:
            details["cache_key"] = cache_key
        super().__init__(message, "CACHE_ERROR", details)


class SecurityError(RAGBaseException):
    """
    Raised when there's a security-related issue.
    """
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "SECURITY_ERROR", details)


# Global exception registry for easy lookup
EXCEPTION_REGISTRY = {
    "CONFIG_ERROR": ConfigurationError,
    "DOCUMENT_PROCESSING_ERROR": DocumentProcessingError,
    "EMBEDDING_ERROR": EmbeddingError,
    "VECTOR_DATABASE_ERROR": VectorDatabaseError,
    "QUERY_ERROR": QueryError,
    "API_ERROR": APIError,
    "RATE_LIMIT_ERROR": RateLimitError,
    "VALIDATION_ERROR": ValidationError,
    "FILE_OPERATION_ERROR": FileOperationError,
    "CACHE_ERROR": CacheError,
    "SECURITY_ERROR": SecurityError,
}


def create_exception(error_code: str, message: str, details: dict = None) -> RAGBaseException:
    """
    Create an exception instance based on error code.

    Args:
        error_code: The error code to create exception for
        message: The error message
        details: Additional details for the exception

    Returns:
        Instance of the appropriate exception class
    """
    exception_class = EXCEPTION_REGISTRY.get(error_code, RAGBaseException)
    return exception_class(message, details=details)


def handle_exception(exception: Exception, context: str = "") -> RAGBaseException:
    """
    Convert a generic exception to an appropriate RAGBaseException.

    Args:
        exception: The original exception
        context: Context information about where the exception occurred

    Returns:
        Appropriate RAGBaseException instance
    """
    if isinstance(exception, RAGBaseException):
        # If it's already a RAGBaseException, just add context if needed
        if context and "context" not in exception.details:
            exception.details["context"] = context
        return exception

    # Map common Python exceptions to RAG exceptions
    if isinstance(exception, FileNotFoundError):
        return FileOperationError(f"File not found: {str(exception)}", details={"context": context})
    elif isinstance(exception, PermissionError):
        return SecurityError(f"Permission denied: {str(exception)}", details={"context": context})
    elif isinstance(exception, ValueError):
        return ValidationError(f"Invalid value: {str(exception)}", details={"context": context})
    elif isinstance(exception, KeyError):
        return ValidationError(f"Missing key: {str(exception)}", details={"context": context})
    elif isinstance(exception, TypeError):
        return ValidationError(f"Type error: {str(exception)}", details={"context": context})
    elif "rate" in str(exception).lower() or "limit" in str(exception).lower():
        return RateLimitError(f"Rate limit error: {str(exception)}", details={"context": context})
    else:
        return RAGBaseException(
            f"Unexpected error: {str(exception)}",
            error_code="UNEXPECTED_ERROR",
            details={"original_exception": str(type(exception).__name__), "context": context}
        )