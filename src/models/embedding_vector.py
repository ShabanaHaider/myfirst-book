"""
EmbeddingVector data model representing a numerical representation of text content in high-dimensional space.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class EmbeddingVector:
    """
    A numerical representation of text content in high-dimensional space.

    Attributes:
        id: Unique identifier (corresponds to DocumentChunk.id)
        vector: The embedding vector values (1024 dimensions for Cohere)
        metadata: JSON containing source file, chunk index, etc.
        collection_name: Qdrant collection name ("myfirst_book")
        created_at: Timestamp of creation
    """

    id: str
    vector: List[float]
    metadata: Dict[str, Any]
    collection_name: str
    created_at: datetime

    def __post_init__(self):
        """Validate the EmbeddingVector after initialization."""
        self._validate()

    def _validate(self):
        """Validate the attributes of the EmbeddingVector."""
        # Cohere multilingual model produces 768-dimensional vectors
        if len(self.vector) != 768:
            raise ValueError(f"Vector must have exactly 768 elements, got {len(self.vector)}")

        if not self.collection_name:
            raise ValueError("collection_name must be specified")

        required_metadata_fields = ["source_file_path", "chunk_index", "character_position", "content_hash"]
        for field in required_metadata_fields:
            if field not in self.metadata:
                raise ValueError(f"metadata must contain required field: {field}")

    def update_metadata(self, new_metadata: Dict[str, Any]) -> None:
        """Update the metadata of the embedding vector."""
        self.metadata.update(new_metadata)