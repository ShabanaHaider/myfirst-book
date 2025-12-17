"""
Chunk persistence module to save to /data/processed_chunks/.
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.models.document_chunk import DocumentChunk
from src.utils.file_utils import ensure_directory_exists, write_file_content
from src.utils.hash_utils import generate_content_hash
from src.utils.logging import StructuredLogger, log_ingestion_event
from src.exceptions import FileOperationError


class ChunkPersistenceService:
    """
    Service for persisting document chunks to the file system.
    """

    def __init__(self, base_directory: str = None):
        """
        Initialize the chunk persistence service.

        Args:
            base_directory: Base directory for saving chunks (defaults to settings.PROCESSED_CHUNKS_DIR)
        """
        from src.config.settings import settings
        self.base_directory = base_directory or settings.PROCESSED_CHUNKS_DIR
        self.logger = StructuredLogger("chunk_persistence_service")
        ensure_directory_exists(self.base_directory)

    def save_chunk(self, chunk: DocumentChunk, subdirectory: str = None) -> bool:
        """
        Save a single document chunk to the file system.

        Args:
            chunk: DocumentChunk object to save
            subdirectory: Optional subdirectory to save the chunk in

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create file path
            directory = self.base_directory
            if subdirectory:
                directory = os.path.join(directory, subdirectory)
                ensure_directory_exists(directory)

            # Create filename based on chunk ID and source file
            safe_source_name = "".join(c for c in chunk.source_file_path if c.isalnum() or c in (' ', '.', '_')).rstrip()
            filename = f"{safe_source_name}_{chunk.id[:8]}.json"
            file_path = os.path.join(directory, filename)

            # Convert chunk to dictionary for JSON serialization
            chunk_data = {
                "id": chunk.id,
                "text_content": chunk.text_content,
                "source_file_path": chunk.source_file_path,
                "chunk_index": chunk.chunk_index,
                "character_position": chunk.character_position,
                "content_hash": chunk.content_hash,
                "created_at": chunk.created_at.isoformat() if hasattr(chunk.created_at, 'isoformat') else str(chunk.created_at),
                "updated_at": chunk.updated_at.isoformat() if chunk.updated_at and hasattr(chunk.updated_at, 'isoformat') else None
            }

            # Write chunk data to file
            success = write_file_content(file_path, json.dumps(chunk_data, indent=2))

            if success:
                self.logger.info(
                    "Chunk saved successfully",
                    chunk_id=chunk.id,
                    file_path=file_path
                )
                log_ingestion_event(
                    event="chunk_saved",
                    file_path=file_path,
                    status="success",
                    chunk_id=chunk.id
                )
            else:
                self.logger.error(
                    "Failed to save chunk",
                    chunk_id=chunk.id,
                    file_path=file_path
                )
                log_ingestion_event(
                    event="chunk_save_failed",
                    file_path=file_path,
                    status="error",
                    chunk_id=chunk.id
                )

            return success

        except Exception as e:
            self.logger.error("Failed to save chunk", chunk_id=chunk.id, error=str(e))
            log_ingestion_event(
                event="chunk_save_failed",
                file_path=chunk.source_file_path,
                status="error",
                chunk_id=chunk.id,
                error=str(e)
            )
            return False

    def save_chunks(self, chunks: List[DocumentChunk], subdirectory: str = None) -> Dict[str, Any]:
        """
        Save multiple document chunks to the file system.

        Args:
            chunks: List of DocumentChunk objects to save
            subdirectory: Optional subdirectory to save the chunks in

        Returns:
            Dictionary with save results
        """
        results = {
            "total_chunks": len(chunks),
            "successful_saves": 0,
            "failed_saves": 0,
            "failed_chunks": []
        }

        for chunk in chunks:
            success = self.save_chunk(chunk, subdirectory)
            if success:
                results["successful_saves"] += 1
            else:
                results["failed_saves"] += 1
                results["failed_chunks"].append({
                    "chunk_id": chunk.id,
                    "source_file": chunk.source_file_path,
                    "error": f"Failed to save chunk {chunk.id}"
                })

        self.logger.info(
            "Chunk batch save completed",
            total_chunks=len(chunks),
            successful_saves=results["successful_saves"],
            failed_saves=results["failed_saves"]
        )

        return results

    def save_chunks_by_source(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        Save chunks organized by their source file directory structure.

        Args:
            chunks: List of DocumentChunk objects to save

        Returns:
            Dictionary with save results
        """
        # Group chunks by source file
        chunks_by_source: Dict[str, List[DocumentChunk]] = {}
        for chunk in chunks:
            source_dir = os.path.dirname(chunk.source_file_path)
            if source_dir not in chunks_by_source:
                chunks_by_source[source_dir] = []
            chunks_by_source[source_dir].append(chunk)

        results = {
            "total_sources": len(chunks_by_source),
            "sources_processed": 0,
            "total_chunks": len(chunks),
            "successful_saves": 0,
            "failed_saves": 0
        }

        for source_dir, source_chunks in chunks_by_source.items():
            # Create a subdirectory based on the source file's directory structure
            # Remove leading slashes and replace path separators with underscores
            safe_subdir = source_dir.strip('/').replace('/', '_').replace('\\', '_')
            if safe_subdir == "":
                safe_subdir = "root"

            source_results = self.save_chunks(source_chunks, safe_subdir)
            results["sources_processed"] += 1
            results["successful_saves"] += source_results["successful_saves"]
            results["failed_saves"] += source_results["failed_saves"]

        return results

    def save_chunk_with_metadata(self, chunk: DocumentChunk, metadata: Dict[str, Any], subdirectory: str = None) -> bool:
        """
        Save a chunk with additional metadata.

        Args:
            chunk: DocumentChunk object to save
            metadata: Additional metadata to save with the chunk
            subdirectory: Optional subdirectory to save the chunk in

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create file path
            directory = self.base_directory
            if subdirectory:
                directory = os.path.join(directory, subdirectory)
                ensure_directory_exists(directory)

            # Create filename based on chunk ID and source file
            safe_source_name = "".join(c for c in chunk.source_file_path if c.isalnum() or c in (' ', '.', '_')).rstrip()
            filename = f"{safe_source_name}_{chunk.id[:8]}.json"
            file_path = os.path.join(directory, filename)

            # Convert chunk to dictionary and add metadata
            chunk_data = {
                "id": chunk.id,
                "text_content": chunk.text_content,
                "source_file_path": chunk.source_file_path,
                "chunk_index": chunk.chunk_index,
                "character_position": chunk.character_position,
                "content_hash": chunk.content_hash,
                "created_at": chunk.created_at.isoformat() if hasattr(chunk.created_at, 'isoformat') else str(chunk.created_at),
                "updated_at": chunk.updated_at.isoformat() if chunk.updated_at and hasattr(chunk.updated_at, 'isoformat') else None,
                "metadata": metadata
            }

            # Write chunk data to file
            success = write_file_content(file_path, json.dumps(chunk_data, indent=2))

            if success:
                self.logger.info(
                    "Chunk with metadata saved successfully",
                    chunk_id=chunk.id,
                    file_path=file_path
                )
            else:
                self.logger.error(
                    "Failed to save chunk with metadata",
                    chunk_id=chunk.id,
                    file_path=file_path
                )

            return success

        except Exception as e:
            self.logger.error("Failed to save chunk with metadata", chunk_id=chunk.id, error=str(e))
            return False

    def load_chunk(self, file_path: str) -> Optional[DocumentChunk]:
        """
        Load a single document chunk from the file system.

        Args:
            file_path: Path to the chunk file

        Returns:
            DocumentChunk object or None if loading failed
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error("Chunk file does not exist", file_path=file_path)
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)

            # Create DocumentChunk from loaded data
            chunk = DocumentChunk(
                id=chunk_data["id"],
                text_content=chunk_data["text_content"],
                source_file_path=chunk_data["source_file_path"],
                chunk_index=chunk_data["chunk_index"],
                character_position=chunk_data["character_position"],
                content_hash=chunk_data["content_hash"],
                created_at=datetime.fromisoformat(chunk_data["created_at"]) if isinstance(chunk_data["created_at"], str) else chunk_data["created_at"]
            )

            # Set updated_at if present
            if chunk_data.get("updated_at"):
                chunk.updated_at = datetime.fromisoformat(chunk_data["updated_at"]) if isinstance(chunk_data["updated_at"], str) else chunk_data["updated_at"]

            return chunk

        except Exception as e:
            self.logger.error("Failed to load chunk", file_path=file_path, error=str(e))
            return None

    def load_chunks_from_directory(self, directory: str = None) -> List[DocumentChunk]:
        """
        Load all chunks from a directory.

        Args:
            directory: Directory to load chunks from (defaults to base directory)

        Returns:
            List of DocumentChunk objects
        """
        if directory is None:
            directory = self.base_directory

        chunks = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    chunk = self.load_chunk(file_path)
                    if chunk:
                        chunks.append(chunk)

        self.logger.info(
            "Chunks loaded from directory",
            directory=directory,
            count=len(chunks)
        )

        return chunks

    def get_chunk_file_path(self, chunk: DocumentChunk, subdirectory: str = None) -> str:
        """
        Get the expected file path for a chunk.

        Args:
            chunk: DocumentChunk object
            subdirectory: Optional subdirectory

        Returns:
            Expected file path for the chunk
        """
        directory = self.base_directory
        if subdirectory:
            directory = os.path.join(directory, subdirectory)
            ensure_directory_exists(directory)

        safe_source_name = "".join(c for c in chunk.source_file_path if c.isalnum() or c in (' ', '.', '_')).rstrip()
        filename = f"{safe_source_name}_{chunk.id[:8]}.json"
        return os.path.join(directory, filename)

    def chunk_exists(self, chunk: DocumentChunk, subdirectory: str = None) -> bool:
        """
        Check if a chunk already exists in the file system.

        Args:
            chunk: DocumentChunk object to check
            subdirectory: Optional subdirectory

        Returns:
            True if chunk exists, False otherwise
        """
        file_path = self.get_chunk_file_path(chunk, subdirectory)
        return os.path.exists(file_path)

    def save_chunks_with_deduplication(self, chunks: List[DocumentChunk], subdirectory: str = None) -> Dict[str, Any]:
        """
        Save chunks with deduplication based on content hash.

        Args:
            chunks: List of DocumentChunk objects to save
            subdirectory: Optional subdirectory to save the chunks in

        Returns:
            Dictionary with save results including deduplication info
        """
        # Group chunks by content hash to identify duplicates
        unique_chunks = {}
        duplicates = []

        for chunk in chunks:
            if chunk.content_hash in unique_chunks:
                duplicates.append(chunk)
            else:
                unique_chunks[chunk.content_hash] = chunk

        unique_chunk_list = list(unique_chunks.values())

        # Save only unique chunks
        save_results = self.save_chunks(unique_chunk_list, subdirectory)

        return {
            "total_input_chunks": len(chunks),
            "unique_chunks": len(unique_chunk_list),
            "duplicates_found": len(duplicates),
            "duplicate_details": [
                {"chunk_id": chunk.id, "source_file": chunk.source_file_path, "content_hash": chunk.content_hash}
                for chunk in duplicates
            ],
            "save_results": save_results
        }

    def validate_saved_chunks(self, chunk_ids: List[str], source_directory: str = None) -> Dict[str, Any]:
        """
        Validate that specified chunks have been saved correctly.

        Args:
            chunk_ids: List of chunk IDs to validate
            source_directory: Directory to look for chunks (defaults to base directory)

        Returns:
            Dictionary with validation results
        """
        if source_directory is None:
            source_directory = self.base_directory

        results = {
            "total_chunks": len(chunk_ids),
            "found_chunks": 0,
            "missing_chunks": [],
            "valid_chunks": 0,
            "invalid_chunks": []
        }

        # Since we don't have a direct mapping from chunk_id to filename, we need to search
        # This is an inefficient approach but works for validation
        all_files = []
        for root, dirs, files in os.walk(source_directory):
            for file in files:
                if file.endswith('.json'):
                    all_files.append(os.path.join(root, file))

        chunk_id_to_path = {}
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    chunk_id_to_path[data.get("id")] = file_path
            except Exception:
                continue  # Skip invalid files

        for chunk_id in chunk_ids:
            if chunk_id in chunk_id_to_path:
                results["found_chunks"] += 1
                # Try to load and validate the chunk
                chunk = self.load_chunk(chunk_id_to_path[chunk_id])
                if chunk and chunk.id == chunk_id:
                    results["valid_chunks"] += 1
                else:
                    results["invalid_chunks"] .append(chunk_id)
            else:
                results["missing_chunks"].append(chunk_id)

        return results

    def health_check(self) -> bool:
        """
        Check if the chunk persistence service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Test by creating a temporary chunk and saving it
            import tempfile
            test_chunk = DocumentChunk(
                id="test-id-123",
                text_content="This is a test chunk for health check",
                source_file_path="test.md",
                chunk_index=0,
                character_position=0,
                content_hash=generate_content_hash("This is a test chunk for health check"),
                created_at=datetime.now()
            )

            # Try to save to a temporary location
            temp_dir = os.path.join(self.base_directory, "health_check")
            ensure_directory_exists(temp_dir)

            success = self.save_chunk(test_chunk, "health_check")

            # Clean up test file
            if success:
                test_file_path = self.get_chunk_file_path(test_chunk, "health_check")
                if os.path.exists(test_file_path):
                    os.remove(test_file_path)

            # Remove temp directory if empty
            try:
                os.rmdir(os.path.join(self.base_directory, "health_check"))
            except OSError:
                pass  # Directory not empty, which is fine

            return success
        except Exception:
            return False