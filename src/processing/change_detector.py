"""
File change detection module using timestamps and content hashes.
"""
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
from src.utils.file_utils import get_file_last_modified, get_file_hash
from src.utils.logging import StructuredLogger, log_ingestion_event
from src.exceptions import FileOperationError


@dataclass
class FileState:
    """Represents the state of a file at a point in time."""
    file_path: str
    last_modified: float
    content_hash: str
    size: int
    checked_at: datetime


class ChangeDetector:
    """
    Service for detecting changes in files using timestamps and content hashes.
    """

    def __init__(self):
        """Initialize the change detector."""
        self.logger = StructuredLogger("change_detector")
        self.known_files: Dict[str, FileState] = {}

    def get_file_state(self, file_path: str) -> Optional[FileState]:
        """
        Get the current state of a file.

        Args:
            file_path: Path to the file

        Returns:
            FileState object or None if file doesn't exist
        """
        try:
            if not os.path.exists(file_path):
                return None

            stat = os.stat(file_path)
            content_hash = get_file_hash(file_path)

            return FileState(
                file_path=file_path,
                last_modified=stat.st_mtime,
                content_hash=content_hash,
                size=stat.st_size,
                checked_at=datetime.now()
            )
        except Exception as e:
            self.logger.error("Failed to get file state", file_path=file_path, error=str(e))
            raise FileOperationError(f"Failed to get state for {file_path}: {str(e)}")

    def has_file_changed(self, file_path: str, previous_state: FileState = None) -> Tuple[bool, str]:
        """
        Check if a file has changed since a previous state.

        Args:
            file_path: Path to the file to check
            previous_state: Previous FileState to compare against

        Returns:
            Tuple of (has_changed, change_type)
        """
        try:
            current_state = self.get_file_state(file_path)

            if current_state is None:
                return False, "file_deleted"

            if previous_state is None:
                # First time seeing this file
                return True, "new_file"

            # Check for changes
            if current_state.content_hash != previous_state.content_hash:
                return True, "content_changed"

            if current_state.last_modified > previous_state.last_modified:
                return True, "modified_time_changed"

            if current_state.size != previous_state.size:
                return True, "size_changed"

            return False, "no_change"

        except Exception as e:
            self.logger.error("Failed to check file change", file_path=file_path, error=str(e))
            raise FileOperationError(f"Failed to check change for {file_path}: {str(e)}")

    def detect_changes_in_directory(
        self,
        directory: str,
        recursive: bool = True,
        file_extensions: List[str] = None
    ) -> Dict[str, Tuple[bool, str, Optional[FileState], Optional[FileState]]]:
        """
        Detect changes in all files in a directory.

        Args:
            directory: Directory to scan
            recursive: Whether to scan recursively
            file_extensions: List of file extensions to check (e.g., ['.md', '.txt'])

        Returns:
            Dictionary mapping file paths to (changed, change_type, previous_state, current_state)
        """
        if file_extensions is None:
            file_extensions = ['.md', '.txt']

        try:
            # Get all files in directory
            all_files = []
            directory_path = Path(directory)

            if recursive:
                for ext in file_extensions:
                    all_files.extend(directory_path.rglob(f"*{ext}"))
            else:
                for ext in file_extensions:
                    all_files.extend(directory_path.glob(f"*{ext}"))

            # Convert to absolute paths
            file_paths = [str(f) for f in all_files]

            changes = {}
            for file_path in file_paths:
                previous_state = self.known_files.get(file_path)
                has_changed, change_type = self.has_file_changed(file_path, previous_state)
                current_state = self.get_file_state(file_path)

                changes[file_path] = (has_changed, change_type, previous_state, current_state)

                # Update known files if there's a change or it's a new file
                if has_changed or previous_state is None:
                    self.known_files[file_path] = current_state

            log_ingestion_event(
                event="change_detection_completed",
                file_path=directory,
                status="success",
                files_checked=len(file_paths),
                files_changed=len([f for f, (changed, _, _, _) in changes.items() if changed])
            )

            return changes

        except Exception as e:
            self.logger.error("Failed to detect changes in directory", directory=directory, error=str(e))
            log_ingestion_event(
                event="change_detection_failed",
                file_path=directory,
                status="error",
                error=str(e)
            )
            raise FileOperationError(f"Failed to detect changes in {directory}: {str(e)}")

    def get_changed_files(
        self,
        directory: str,
        recursive: bool = True,
        file_extensions: List[str] = None
    ) -> Dict[str, str]:
        """
        Get only the files that have changed.

        Args:
            directory: Directory to scan
            recursive: Whether to scan recursively
            file_extensions: List of file extensions to check

        Returns:
            Dictionary mapping file paths to change types
        """
        changes = self.detect_changes_in_directory(directory, recursive, file_extensions)
        changed_files = {
            file_path: change_type
            for file_path, (has_changed, change_type, _, _) in changes.items()
            if has_changed
        }
        return changed_files

    def mark_file_as_processed(self, file_path: str):
        """
        Mark a file as processed by storing its current state.

        Args:
            file_path: Path to the file that was processed
        """
        try:
            state = self.get_file_state(file_path)
            if state:
                self.known_files[file_path] = state
        except Exception as e:
            self.logger.error("Failed to mark file as processed", file_path=file_path, error=str(e))

    def mark_files_as_processed(self, file_paths: List[str]):
        """
        Mark multiple files as processed.

        Args:
            file_paths: List of file paths to mark as processed
        """
        for file_path in file_paths:
            self.mark_file_as_processed(file_path)

    def get_new_files(self, directory: str, recursive: bool = True, file_extensions: List[str] = None) -> List[str]:
        """
        Get files that are new (not seen before).

        Args:
            directory: Directory to scan
            recursive: Whether to scan recursively
            file_extensions: List of file extensions to check

        Returns:
            List of new file paths
        """
        changes = self.detect_changes_in_directory(directory, recursive, file_extensions)
        new_files = [
            file_path
            for file_path, (has_changed, change_type, previous_state, _) in changes.items()
            if has_changed and change_type == "new_file"
        ]
        return new_files

    def get_deleted_files(self, directory: str, file_extensions: List[str] = None) -> List[str]:
        """
        Get files that have been deleted (were known but no longer exist).

        Args:
            directory: Directory to scan
            file_extensions: List of file extensions to check

        Returns:
            List of deleted file paths
        """
        if file_extensions is None:
            file_extensions = ['.md', '.txt']

        deleted_files = []
        for file_path, known_state in self.known_files.items():
            if (file_path.startswith(directory) and
                any(file_path.endswith(ext) for ext in file_extensions) and
                not os.path.exists(file_path)):
                deleted_files.append(file_path)

        return deleted_files

    def update_known_files(self, file_states: Dict[str, FileState]):
        """
        Update the known files with new states.

        Args:
            file_states: Dictionary of file paths to FileState objects
        """
        self.known_files.update(file_states)

    def clear_known_files(self):
        """Clear all known file states."""
        self.known_files.clear()

    def save_known_files_state(self, state_file_path: str):
        """
        Save the current known file states to a file.

        Args:
            state_file_path: Path to save the state file
        """
        try:
            import json

            state_data = {}
            for file_path, file_state in self.known_files.items():
                state_data[file_path] = {
                    "file_path": file_state.file_path,
                    "last_modified": file_state.last_modified,
                    "content_hash": file_state.content_hash,
                    "size": file_state.size,
                    "checked_at": file_state.checked_at.isoformat()
                }

            with open(state_file_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2)

            self.logger.info("Saved file state", state_file_path=state_file_path)
        except Exception as e:
            self.logger.error("Failed to save file state", state_file_path=state_file_path, error=str(e))
            raise FileOperationError(f"Failed to save state to {state_file_path}: {str(e)}")

    def load_known_files_state(self, state_file_path: str):
        """
        Load known file states from a file.

        Args:
            state_file_path: Path to load the state file from
        """
        try:
            import json
            from datetime import datetime

            if not os.path.exists(state_file_path):
                self.logger.info("State file does not exist, starting fresh", state_file_path=state_file_path)
                return

            with open(state_file_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            for file_path, data in state_data.items():
                self.known_files[file_path] = FileState(
                    file_path=data["file_path"],
                    last_modified=data["last_modified"],
                    content_hash=data["content_hash"],
                    size=data["size"],
                    checked_at=datetime.fromisoformat(data["checked_at"])
                )

            self.logger.info("Loaded file state", state_file_path=state_file_path)
        except Exception as e:
            self.logger.error("Failed to load file state", state_file_path=state_file_path, error=str(e))
            raise FileOperationError(f"Failed to load state from {state_file_path}: {str(e)}")

    def get_change_summary(self, directory: str, file_extensions: List[str] = None) -> Dict[str, any]:
        """
        Get a summary of changes in a directory.

        Args:
            directory: Directory to scan
            file_extensions: List of file extensions to check

        Returns:
            Dictionary with change summary
        """
        changes = self.detect_changes_in_directory(directory, file_extensions=file_extensions)

        summary = {
            "directory": directory,
            "total_files": len(changes),
            "changed_files": 0,
            "new_files": 0,
            "unchanged_files": 0,
            "change_types": {},
            "timestamp": datetime.now().isoformat()
        }

        for file_path, (has_changed, change_type, _, _) in changes.items():
            if has_changed:
                summary["changed_files"] += 1
                if change_type == "new_file":
                    summary["new_files"] += 1

                if change_type in summary["change_types"]:
                    summary["change_types"][change_type] += 1
                else:
                    summary["change_types"][change_type] = 1
            else:
                summary["unchanged_files"] += 1

        return summary

    def health_check(self) -> bool:
        """
        Check if the change detector is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Create a temporary test file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write("test content")
                temp_path = f.name

            # Check if we can detect the new file
            state = self.get_file_state(temp_path)
            self.known_files[temp_path] = state

            # Modify the file
            with open(temp_path, 'w') as f:
                f.write("modified content")

            # Check if we can detect the change
            has_changed, change_type = self.has_file_changed(temp_path, state)

            # Clean up
            os.unlink(temp_path)

            return has_changed and change_type == "content_changed"
        except Exception:
            return False