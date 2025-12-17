"""
SourceFile data model representing the original markdown document from which chunks are derived.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SourceFile:
    """
    The original markdown document from which chunks are derived.

    Attributes:
        file_path: Path to the source markdown file
        last_modified: Timestamp of last modification
        content_hash: Hash of file content for change detection
        status: Processing status (pending, processed, failed)
        chunks_count: Number of chunks created from this file
        created_at: Timestamp of first detection
        updated_at: Timestamp of last update
    """

    file_path: str
    last_modified: datetime
    content_hash: str
    status: str  # "pending", "processed", "failed"
    chunks_count: int = 0
    created_at: datetime = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate the SourceFile after initialization."""
        if self.created_at is None:
            self.created_at = datetime.now()
        self._validate()

    def _validate(self):
        """Validate the attributes of the SourceFile."""
        if not self.file_path:
            raise ValueError("file_path must be a valid markdown file path")

        valid_statuses = ["pending", "processed", "failed"]
        if self.status not in valid_statuses:
            raise ValueError(f"status must be one of: {valid_statuses}")

        if self.chunks_count < 0:
            raise ValueError("chunks_count must be non-negative")

    def mark_processed(self, chunks_count: int) -> None:
        """Mark the file as processed with the given number of chunks."""
        self.status = "processed"
        self.chunks_count = chunks_count
        self.updated_at = datetime.now()

    def mark_failed(self) -> None:
        """Mark the file as failed processing."""
        self.status = "failed"
        self.updated_at = datetime.now()

    def mark_pending(self) -> None:
        """Mark the file as pending processing."""
        self.status = "pending"
        self.updated_at = datetime.now()