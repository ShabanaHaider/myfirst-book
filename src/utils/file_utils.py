"""
File utility functions for path handling and file operations.
"""
import os
import hashlib
from pathlib import Path
from typing import List, Optional
import asyncio
from asyncio import Lock


def get_all_markdown_files(directory: str) -> List[str]:
    """
    Get all markdown files in the specified directory and its subdirectories.

    Args:
        directory: The directory to search for markdown files

    Returns:
        List of paths to markdown files
    """
    markdown_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.md', '.markdown')):
                markdown_files.append(os.path.join(root, file))
    return sorted(markdown_files)


def get_file_hash(file_path: str) -> str:
    """
    Get the SHA256 hash of a file's content.

    Args:
        file_path: Path to the file

    Returns:
        SHA256 hash of the file content
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read the file in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_file_last_modified(file_path: str) -> float:
    """
    Get the last modified timestamp of a file.

    Args:
        file_path: Path to the file

    Returns:
        Last modified timestamp as a float
    """
    return os.path.getmtime(file_path)


def ensure_directory_exists(directory: str) -> bool:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        directory: Path to the directory

    Returns:
        True if directory exists or was created, False otherwise
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def read_file_content(file_path: str) -> Optional[str]:
    """
    Read the content of a file.

    Args:
        file_path: Path to the file

    Returns:
        Content of the file as a string, or None if reading fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception:
        return None


def write_file_content(file_path: str, content: str) -> bool:
    """
    Write content to a file.

    Args:
        file_path: Path to the file
        content: Content to write

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure the directory exists before writing
        directory = os.path.dirname(file_path)
        if directory:
            ensure_directory_exists(directory)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return True
    except Exception:
        return False


class FileLockManager:
    """
    A simple file lock manager to prevent concurrent access to the same file.
    """
    def __init__(self):
        self._locks = {}
        self._global_lock = Lock()

    async def get_lock(self, file_path: str) -> Lock:
        """
        Get a lock for a specific file path.

        Args:
            file_path: Path to the file

        Returns:
            asyncio.Lock for the file
        """
        async with self._global_lock:
            if file_path not in self._locks:
                self._locks[file_path] = Lock()
            return self._locks[file_path]