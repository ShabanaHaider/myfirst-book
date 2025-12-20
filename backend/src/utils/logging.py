"""
Logging module with structured logging.
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional


class StructuredLogger:
    """
    A structured logger that outputs logs in JSON format for better analysis.
    """

    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize the structured logger.

        Args:
            name: Name of the logger
            level: Logging level (default: INFO)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Create a handler that outputs to stdout
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = StructuredFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _log(self, level: int, message: str, **kwargs) -> None:
        """
        Internal method to log messages with structured data.

        Args:
            level: Logging level
            message: Log message
            **kwargs: Additional structured data
        """
        extra_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message
        }
        extra_data.update(kwargs)

        self.logger.log(level, json.dumps(extra_data))

    def debug(self, message: str, **kwargs) -> None:
        """Log a debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log an info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log a warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log an error message."""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log a critical message."""
        self._log(logging.CRITICAL, message, **kwargs)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in structured JSON format.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add any extra fields that were passed to the log call
        if hasattr(record, 'args') and record.args:
            log_entry.update(record.args)

        return json.dumps(log_entry)


def setup_logging(level: int = logging.INFO) -> StructuredLogger:
    """
    Set up and configure the structured logging system.

    Args:
        level: Logging level (default: INFO)

    Returns:
        Configured StructuredLogger instance
    """
    # Set the root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create a console handler with structured formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)

    # Return a structured logger for the main application
    return StructuredLogger("rag_chatbot", level)


def log_api_call(operation: str, status: str, duration_ms: float, **kwargs) -> None:
    """
    Log an API call with structured data.

    Args:
        operation: The API operation being performed
        status: The status of the operation (success, error, etc.)
        duration_ms: Duration of the operation in milliseconds
        **kwargs: Additional data to log
    """
    logger = StructuredLogger("api")
    logger.info(
        f"API call completed: {operation}",
        operation=operation,
        status=status,
        duration_ms=duration_ms,
        **kwargs
    )


def log_embedding_operation(operation: str, status: str, embedding_count: int, **kwargs) -> None:
    """
    Log an embedding operation with structured data.

    Args:
        operation: The embedding operation being performed
        status: The status of the operation
        embedding_count: Number of embeddings processed
        **kwargs: Additional data to log
    """
    logger = StructuredLogger("embedding")
    logger.info(
        f"Embedding operation: {operation}",
        operation=operation,
        status=status,
        embedding_count=embedding_count,
        **kwargs
    )


def log_ingestion_event(event: str, file_path: str, status: str, **kwargs) -> None:
    """
    Log an ingestion event with structured data.

    Args:
        event: The ingestion event type
        file_path: Path of the file being processed
        status: Status of the operation
        **kwargs: Additional data to log
    """
    logger = StructuredLogger("ingestion")
    logger.info(
        f"Ingestion event: {event}",
        event=event,
        file_path=file_path,
        status=status,
        **kwargs
    )


def log_query_event(query: str, result_count: int, response_time_ms: float, **kwargs) -> None:
    """
    Log a query event with structured data.

    Args:
        query: The query text
        result_count: Number of results returned
        response_time_ms: Response time in milliseconds
        **kwargs: Additional data to log
    """
    logger = StructuredLogger("query")
    logger.info(
        "Query processed",
        query=query[:100] + "..." if len(query) > 100 else query,  # Truncate long queries
        result_count=result_count,
        response_time_ms=response_time_ms,
        **kwargs
    )