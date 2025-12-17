"""
DocumentChunk data model representing a semantic piece of text extracted from source documentation.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class DocumentChunk:
    """
    Represents a semantic piece of text extracted from source documentation.

    Attributes:
        id: Unique identifier for the chunk
        text_content: The actual text content of the chunk (max 512 tokens)
        source_file_path: Path to the original markdown file
        chunk_index: Position of this chunk in the original document
        character_position: Start position in original document
        content_hash: Hash for change detection
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """

    id: str
    text_content: str
    source_file_path: str
    chunk_index: int
    character_position: int
    content_hash: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate the DocumentChunk after initialization."""
        self._validate()

    def _validate(self):
        """Validate the attributes of the DocumentChunk."""
        if len(self.text_content) > 512 * 4:  # Rough token estimation (4 chars per token)
            raise ValueError("text_content exceeds maximum token limit (512 tokens)")

        if not self.source_file_path:
            raise ValueError("source_file_path must be a valid path reference")

        if self.chunk_index < 0:
            raise ValueError("chunk_index must be non-negative")

        if self.character_position < 0:
            raise ValueError("character_position must be non-negative")

    def update(self, text_content: Optional[str] = None,
               content_hash: Optional[str] = None) -> None:
        """Update the chunk with new content and update the timestamp."""
        if text_content is not None:
            self.text_content = text_content
        if content_hash is not None:
            self.content_hash = content_hash
        self.updated_at = datetime.now()