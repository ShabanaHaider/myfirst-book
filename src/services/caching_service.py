"""
Caching service to avoid reprocessing unchanged content.
"""
import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import os


class EmbeddingCache:
    """
    Service for caching embeddings to avoid reprocessing unchanged content.
    """

    def __init__(self, cache_dir: str = "data/embedding_cache/"):
        """Initialize the embedding cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "embeddings_cache.pkl"
        self._cache = self._load_cache()
        self._metadata_file = self.cache_dir / "cache_metadata.json"
        self._metadata = self._load_metadata()

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file if it exists."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logging.warning(f"Failed to load cache from {self.cache_file}: {e}")
                return {}
        return {}

    def _save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self._cache, f)
        except Exception as e:
            logging.error(f"Failed to save cache to {self.cache_file}: {e}")

    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from file if it exists."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load metadata from {self._metadata_file}: {e}")
                return {}
        return {}

    def _save_metadata(self):
        """Save cache metadata to file."""
        try:
            with open(self._metadata_file, 'w') as f:
                json.dump(self._metadata, f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Failed to save metadata to {self._metadata_file}: {e}")

    def get_embedding(self, content_hash: str) -> Optional[List[float]]:
        """
        Get cached embedding for a content hash.

        Args:
            content_hash: Hash of the content to look up

        Returns:
            Cached embedding if found, None otherwise
        """
        return self._cache.get(content_hash)

    def set_embedding(self, content_hash: str, embedding: List[float], source_file: str = ""):
        """
        Store an embedding in the cache.

        Args:
            content_hash: Hash of the content
            embedding: The embedding vector to cache
            source_file: Optional source file path for metadata
        """
        self._cache[content_hash] = embedding
        self._metadata[content_hash] = {
            "source_file": source_file,
            "cached_at": datetime.now().isoformat(),
            "embedding_length": len(embedding)
        }
        self._save_cache()
        self._save_metadata()

    def is_content_cached(self, content_hash: str) -> bool:
        """
        Check if content with the given hash is already cached.

        Args:
            content_hash: Hash of the content to check

        Returns:
            True if content is cached, False otherwise
        """
        return content_hash in self._cache

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cached_items": len(self._cache),
            "cache_size_mb": os.path.getsize(self.cache_file) / (1024 * 1024) if self.cache_file.exists() else 0,
            "metadata_items": len(self._metadata)
        }

    def clear_cache(self):
        """Clear the entire cache."""
        self._cache.clear()
        self._metadata.clear()
        self._save_cache()
        self._save_metadata()

    def remove_by_content_hash(self, content_hash: str):
        """
        Remove a specific item from the cache.

        Args:
            content_hash: Hash of the content to remove
        """
        if content_hash in self._cache:
            del self._cache[content_hash]
        if content_hash in self._metadata:
            del self._metadata[content_hash]
        self._save_cache()
        self._save_metadata()

    def cleanup_old_entries(self, days: int = 30):
        """
        Remove cache entries older than the specified number of days.

        Args:
            days: Number of days to keep cache entries
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        to_remove = []

        for content_hash, metadata in self._metadata.items():
            cached_at = datetime.fromisoformat(metadata["cached_at"])
            if cached_at < cutoff_date:
                to_remove.append(content_hash)

        for content_hash in to_remove:
            del self._cache[content_hash]
            del self._metadata[content_hash]

        if to_remove:
            logging.info(f"Removed {len(to_remove)} old cache entries")
            self._save_cache()
            self._save_metadata()


class ContentHasher:
    """
    Service for generating consistent content hashes.
    """

    @staticmethod
    def generate_content_hash(content: str, additional_metadata: Optional[Dict] = None) -> str:
        """
        Generate a hash for content combined with metadata.

        Args:
            content: The content to hash
            additional_metadata: Additional metadata to include in hash

        Returns:
            SHA-256 hash of the content and metadata
        """
        # Create a string that combines content and metadata
        content_to_hash = content
        if additional_metadata:
            # Sort keys to ensure consistent hashing
            sorted_metadata = json.dumps(additional_metadata, sort_keys=True)
            content_to_hash = f"{content}||{sorted_metadata}"

        # Generate SHA-256 hash
        return hashlib.sha256(content_to_hash.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_file_hash(file_path: str) -> str:
        """
        Generate a hash for a file's content.

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 hash of the file content
        """
        with open(file_path, 'rb') as f:
            file_content = f.read()
            return hashlib.sha256(file_content).hexdigest()


class CachingService:
    """
    Main caching service that combines embedding cache and content hashing.
    """

    def __init__(self, cache_dir: str = "data/embedding_cache/"):
        self.embedding_cache = EmbeddingCache(cache_dir)
        self.content_hasher = ContentHasher()

    def get_cached_embedding(self, content: str, metadata: Optional[Dict] = None) -> Optional[List[float]]:
        """
        Get cached embedding for content if it exists.

        Args:
            content: Content to check for cached embedding
            metadata: Additional metadata to include in hash

        Returns:
            Cached embedding if found, None otherwise
        """
        content_hash = self.content_hasher.generate_content_hash(content, metadata)
        return self.embedding_cache.get_embedding(content_hash)

    def cache_embedding(self, content: str, embedding: List[float], metadata: Optional[Dict] = None, source_file: str = ""):
        """
        Cache an embedding for content.

        Args:
            content: Content that was embedded
            embedding: The embedding vector to cache
            metadata: Additional metadata to include in hash
            source_file: Optional source file path for metadata
        """
        content_hash = self.content_hasher.generate_content_hash(content, metadata)
        self.embedding_cache.set_embedding(content_hash, embedding, source_file)

    def is_content_cached(self, content: str, metadata: Optional[Dict] = None) -> bool:
        """
        Check if content has been cached.

        Args:
            content: Content to check
            metadata: Additional metadata to include in hash

        Returns:
            True if content is cached, False otherwise
        """
        content_hash = self.content_hasher.generate_content_hash(content, metadata)
        return self.embedding_cache.is_content_cached(content_hash)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        return self.embedding_cache.get_cache_stats()