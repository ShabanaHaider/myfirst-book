"""
File traversal service to list markdown files recursively.
"""
import os
from pathlib import Path
from typing import List, Optional
from src.utils.file_utils import get_all_markdown_files
from src.utils.logging import StructuredLogger
from src.exceptions import FileOperationError


class FileTraversalService:
    """
    Service for traversing directories and listing markdown files.
    """

    def __init__(self):
        """Initialize the file traversal service."""
        self.logger = StructuredLogger("file_traversal_service")

    def get_markdown_files(self, directory: str, recursive: bool = True) -> List[str]:
        """
        Get all markdown files in the specified directory.

        Args:
            directory: The directory to search for markdown files
            recursive: Whether to search recursively in subdirectories

        Returns:
            List of paths to markdown files
        """
        try:
            if not os.path.isdir(directory):
                raise FileOperationError(f"Directory does not exist: {directory}")

            if recursive:
                # Use the utility function to get all markdown files recursively
                markdown_files = get_all_markdown_files(directory)
            else:
                # Get only markdown files in the specified directory (not subdirectories)
                markdown_files = []
                for file in os.listdir(directory):
                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path) and file.lower().endswith(('.md', '.markdown')):
                        markdown_files.append(file_path)

            self.logger.info(
                "Found markdown files",
                directory=directory,
                recursive=recursive,
                count=len(markdown_files)
            )

            return sorted(markdown_files)  # Return sorted for consistency

        except Exception as e:
            self.logger.error("Failed to traverse directory", directory=directory, error=str(e))
            raise FileOperationError(f"Failed to traverse directory {directory}: {str(e)}")

    def get_markdown_files_with_filters(
        self,
        directory: str,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get markdown files with filtering options.

        Args:
            directory: The directory to search for markdown files
            exclude_patterns: List of patterns to exclude from results
            include_patterns: List of patterns to include (if specified, only files matching these will be included)

        Returns:
            List of paths to markdown files matching the criteria
        """
        if exclude_patterns is None:
            exclude_patterns = []
        if include_patterns is None:
            include_patterns = []

        try:
            all_files = self.get_markdown_files(directory)

            filtered_files = []
            for file_path in all_files:
                # Check if file should be excluded
                should_exclude = any(pattern in file_path for pattern in exclude_patterns)

                # Check if file should be included (if include patterns are specified)
                should_include = not include_patterns or any(pattern in file_path for pattern in include_patterns)

                if not should_exclude and should_include:
                    filtered_files.append(file_path)

            self.logger.info(
                "Filtered markdown files",
                directory=directory,
                exclude_patterns=exclude_patterns,
                include_patterns=include_patterns,
                count=len(filtered_files)
            )

            return filtered_files

        except Exception as e:
            self.logger.error(
                "Failed to filter markdown files",
                directory=directory,
                exclude_patterns=exclude_patterns,
                include_patterns=include_patterns,
                error=str(e)
            )
            raise FileOperationError(f"Failed to filter markdown files: {str(e)}")

    def get_file_info(self, file_path: str) -> dict:
        """
        Get information about a specific file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file information
        """
        try:
            path = Path(file_path)
            stat = path.stat()

            return {
                "file_path": file_path,
                "size_bytes": stat.st_size,
                "last_modified": stat.st_mtime,
                "created": stat.st_ctime,
                "is_file": path.is_file(),
                "extension": path.suffix.lower(),
                "name": path.name,
                "directory": str(path.parent)
            }
        except Exception as e:
            self.logger.error("Failed to get file info", file_path=file_path, error=str(e))
            raise FileOperationError(f"Failed to get file info for {file_path}: {str(e)}")

    def get_files_info(self, file_paths: List[str]) -> List[dict]:
        """
        Get information about multiple files.

        Args:
            file_paths: List of file paths

        Returns:
            List of dictionaries with file information
        """
        files_info = []
        for file_path in file_paths:
            try:
                info = self.get_file_info(file_path)
                files_info.append(info)
            except Exception as e:
                # Log error but continue processing other files
                self.logger.error("Failed to get info for file", file_path=file_path, error=str(e))
                files_info.append({
                    "file_path": file_path,
                    "error": str(e),
                    "available_info": {"file_path": file_path, "is_available": False}
                })

        return files_info

    def validate_directory_structure(self, directory: str, required_subdirs: Optional[List[str]] = None) -> dict:
        """
        Validate the directory structure for expected content.

        Args:
            directory: Directory to validate
            required_subdirs: List of required subdirectories

        Returns:
            Dictionary with validation results
        """
        if required_subdirs is None:
            required_subdirs = []

        try:
            validation_result = {
                "directory": directory,
                "is_valid": True,
                "issues": [],
                "warnings": [],
                "stats": {}
            }

            if not os.path.isdir(directory):
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"Directory does not exist: {directory}")
                return validation_result

            # Check for required subdirectories
            for required_subdir in required_subdirs:
                required_path = os.path.join(directory, required_subdir)
                if not os.path.isdir(required_path):
                    validation_result["warnings"].append(f"Missing expected subdirectory: {required_subdir}")

            # Get statistics
            all_items = os.listdir(directory)
            subdirs = [item for item in all_items if os.path.isdir(os.path.join(directory, item))]
            files = [item for item in all_items if os.path.isfile(os.path.join(directory, item))]

            validation_result["stats"] = {
                "total_items": len(all_items),
                "subdirectories": len(subdirs),
                "files": len(files),
                "markdown_files": len([f for f in files if f.lower().endswith(('.md', '.markdown'))])
            }

            return validation_result

        except Exception as e:
            self.logger.error("Failed to validate directory structure", directory=directory, error=str(e))
            raise FileOperationError(f"Failed to validate directory structure: {str(e)}")

    def get_unique_directories(self, file_paths: List[str]) -> List[str]:
        """
        Get unique directories from a list of file paths.

        Args:
            file_paths: List of file paths

        Returns:
            List of unique directory paths
        """
        directories = set()
        for file_path in file_paths:
            directory = os.path.dirname(file_path)
            if directory:
                directories.add(directory)
        return sorted(list(directories))

    def health_check(self) -> bool:
        """
        Check if the file traversal service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Test basic functionality by checking if we can access the current directory
            current_dir = os.getcwd()
            if os.path.isdir(current_dir):
                return True
            return False
        except Exception:
            return False