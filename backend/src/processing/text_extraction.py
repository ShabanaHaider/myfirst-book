"""
Text extraction module to clean and normalize markdown content.
"""
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import markdown
from bs4 import BeautifulSoup
from src.utils.file_utils import read_file_content
from src.utils.text_utils import remove_boilerplate_content, clean_text, normalize_whitespace
from src.utils.hash_utils import generate_file_hash_from_content
from src.utils.logging import StructuredLogger, log_ingestion_event
from src.exceptions import DocumentProcessingError


class TextExtractionService:
    """
    Service for extracting text content from markdown files.
    """

    def __init__(self):
        """Initialize the text extraction service."""
        self.logger = StructuredLogger("text_extraction_service")

    def extract_text_from_markdown(self, file_path: str, remove_boilerplate: bool = True) -> Dict[str, any]:
        """
        Extract text content from a markdown file.

        Args:
            file_path: Path to the markdown file
            remove_boilerplate: Whether to remove boilerplate content (frontmatter, etc.)

        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            # Read the file content
            content = read_file_content(file_path)
            if content is None:
                raise DocumentProcessingError(f"Could not read file: {file_path}")

            original_content = content
            content_hash = generate_file_hash_from_content(content)

            # Remove boilerplate if requested
            if remove_boilerplate:
                content = remove_boilerplate_content(content)

            # Convert markdown to plain text
            text_content = self._markdown_to_text(content)

            # Clean and normalize the text
            cleaned_text = clean_text(text_content)
            normalized_text = normalize_whitespace(cleaned_text)

            # Get file info
            file_info = self._get_file_info(file_path)

            result = {
                "file_path": file_path,
                "original_content": original_content,
                "extracted_text": normalized_text,
                "content_hash": content_hash,
                "file_info": file_info,
                "extraction_metadata": {
                    "original_length": len(original_content),
                    "extracted_length": len(normalized_text),
                    "boilerplate_removed": remove_boilerplate,
                    "extraction_time": __import__('datetime').datetime.now().isoformat()
                }
            }

            log_ingestion_event(
                event="text_extraction_success",
                file_path=file_path,
                status="success",
                extracted_length=len(normalized_text)
            )

            return result

        except Exception as e:
            self.logger.error("Failed to extract text from markdown", file_path=file_path, error=str(e))
            log_ingestion_event(
                event="text_extraction_failed",
                file_path=file_path,
                status="error",
                error=str(e)
            )
            raise DocumentProcessingError(f"Failed to extract text from {file_path}: {str(e)}")

    def _markdown_to_text(self, markdown_content: str) -> str:
        """
        Convert markdown content to plain text.

        Args:
            markdown_content: Raw markdown content

        Returns:
            Plain text content
        """
        try:
            # Convert markdown to HTML
            html = markdown.markdown(markdown_content)

            # Parse HTML and extract text
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            return text
        except Exception as e:
            self.logger.error("Failed to convert markdown to text", error=str(e))
            raise

    def extract_text_from_multiple_files(self, file_paths: List[str], remove_boilerplate: bool = True) -> List[Dict[str, any]]:
        """
        Extract text from multiple markdown files.

        Args:
            file_paths: List of file paths to process
            remove_boilerplate: Whether to remove boilerplate content

        Returns:
            List of dictionaries with extracted content for each file
        """
        results = []
        successful = 0
        failed = 0

        for file_path in file_paths:
            try:
                result = self.extract_text_from_markdown(file_path, remove_boilerplate)
                results.append(result)
                successful += 1
            except Exception as e:
                self.logger.error("Failed to process file in batch", file_path=file_path, error=str(e))
                results.append({
                    "file_path": file_path,
                    "error": str(e),
                    "success": False
                })
                failed += 1

        self.logger.info(
            "Batch text extraction completed",
            total_files=len(file_paths),
            successful=successful,
            failed=failed
        )

        return results

    def _get_file_info(self, file_path: str) -> Dict[str, any]:
        """
        Get information about a file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file information
        """
        path = Path(file_path)
        stat = path.stat()

        return {
            "name": path.name,
            "stem": path.stem,  # Name without extension
            "suffix": path.suffix,
            "parent": str(path.parent),
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
            "created_time": stat.st_ctime
        }

    def detect_document_type(self, content: str) -> str:
        """
        Detect the type of document based on its content.

        Args:
            content: Document content to analyze

        Returns:
            Document type string
        """
        # Check for common document type indicators
        content_lower = content.lower()

        if 'frontmatter' in content_lower or content.startswith('---'):
            return 'docusaurus'
        elif '# ' in content or '## ' in content or '### ' in content:
            return 'standard_markdown'
        elif '<!doctype html' in content_lower or '<html' in content_lower:
            return 'html'
        else:
            return 'plain_text'

    def extract_metadata_from_content(self, content: str) -> Dict[str, any]:
        """
        Extract metadata from markdown content (like frontmatter).

        Args:
            content: Raw markdown content

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}

        # Extract YAML frontmatter if present
        frontmatter_pattern = r'^---\n(.*?)\n---\n'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            frontmatter_content = match.group(1)
            metadata['frontmatter'] = self._parse_frontmatter(frontmatter_content)
            # Remove frontmatter from content for further processing
            content = content[len(match.group(0)):]

        # Extract other metadata
        metadata['has_frontmatter'] = bool(match)
        metadata['content_length'] = len(content)

        # Extract title if present
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()

        return metadata

    def detect_duplicate_content(self, content: str, existing_contents: List[str], threshold: float = 0.8) -> bool:
        """
        Detect if content is a duplicate of existing content.

        Args:
            content: Content to check for duplication
            existing_contents: List of existing content to compare against
            threshold: Similarity threshold for considering content as duplicate (0.0-1.0)

        Returns:
            True if content is considered a duplicate, False otherwise
        """
        import difflib

        for existing_content in existing_contents:
            similarity = difflib.SequenceMatcher(None, content.lower(), existing_content.lower()).ratio()
            if similarity >= threshold:
                return True

        return False

    def _parse_frontmatter(self, frontmatter_content: str) -> Dict[str, any]:
        """
        Parse YAML frontmatter content.

        Args:
            frontmatter_content: Raw frontmatter content

        Returns:
            Dictionary with parsed frontmatter
        """
        try:
            # Simple parsing of YAML frontmatter
            # In a real implementation, you'd use a proper YAML parser like PyYAML
            metadata = {}
            lines = frontmatter_content.strip().split('\n')

            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')  # Remove quotes
                    metadata[key] = value

            return metadata
        except Exception as e:
            self.logger.warning("Failed to parse frontmatter", error=str(e))
            return {}

    def extract_sections(self, content: str) -> List[Dict[str, any]]:
        """
        Extract sections from markdown content based on headers.

        Args:
            content: Markdown content

        Returns:
            List of sections with content
        """
        sections = []
        lines = content.split('\n')

        current_section = {
            "title": "Introduction",  # Default title for content before first header
            "content": "",
            "level": 0,
            "start_line": 0
        }

        for i, line in enumerate(lines):
            # Check for markdown headers
            header_match = re.match(r'^(#{1,6})\s+(.+)', line)
            if header_match:
                # Save the previous section if it has content
                if current_section["content"].strip():
                    sections.append(current_section)

                # Start a new section
                hashes = header_match.group(1)
                title = header_match.group(2).strip()
                current_section = {
                    "title": title,
                    "content": "",
                    "level": len(hashes),
                    "start_line": i
                }
            else:
                current_section["content"] += line + "\n"

        # Add the last section
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def extract_text_from_markdown_with_fallback(self, file_path: str, remove_boilerplate: bool = True) -> Dict[str, any]:
        """
        Extract text from markdown with fallback mechanisms for malformed content.

        Args:
            file_path: Path to the markdown file
            remove_boilerplate: Whether to remove boilerplate content

        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            # First, try normal extraction
            return self.extract_text_from_markdown(file_path, remove_boilerplate)
        except Exception as e:
            self.logger.warning(
                "Normal extraction failed, trying fallback method",
                file_path=file_path,
                error=str(e)
            )

            # Fallback: read as plain text and do basic processing
            content = read_file_content(file_path)
            if content is None:
                raise DocumentProcessingError(f"Could not read file: {file_path}")

            # Basic fallback processing - just clean the text
            cleaned_content = clean_text(content)
            if remove_boilerplate:
                cleaned_content = remove_boilerplate_content(cleaned_content)

            file_info = self._get_file_info(file_path)
            content_hash = generate_file_hash_from_content(cleaned_content)

            result = {
                "file_path": file_path,
                "original_content": content,
                "extracted_text": cleaned_content,
                "content_hash": content_hash,
                "file_info": file_info,
                "extraction_metadata": {
                    "original_length": len(content),
                    "extracted_length": len(cleaned_content),
                    "boilerplate_removed": remove_boilerplate,
                    "extraction_time": __import__('datetime').datetime.now().isoformat(),
                    "fallback_used": True,
                    "original_error": str(e)
                }
            }

            log_ingestion_event(
                event="text_extraction_fallback_used",
                file_path=file_path,
                status="success_with_fallback",
                extracted_length=len(cleaned_content),
                original_error=str(e)
            )

            return result

    def validate_extraction_quality(self, extracted_text: str, original_content: str) -> Dict[str, any]:
        """
        Validate the quality of text extraction.

        Args:
            extracted_text: The extracted text
            original_content: The original content

        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "issues": [],
            "quality_metrics": {}
        }

        # Calculate extraction ratio
        original_length = len(original_content)
        extracted_length = len(extracted_text)

        if original_length > 0:
            extraction_ratio = extracted_length / original_length
            validation_result["quality_metrics"]["extraction_ratio"] = extraction_ratio

            # Check if too much content was lost
            if extraction_ratio < 0.1:  # Less than 10% of original content
                validation_result["is_valid"] = False
                validation_result["issues"].append("Extraction ratio is too low - most content was lost")

        # Check for empty extraction
        if not extracted_text.strip():
            validation_result["is_valid"] = False
            validation_result["issues"].append("Extracted text is empty")

        # Check for excessive boilerplate
        if original_length > 0:
            boilerplate_ratio = (original_length - extracted_length) / original_length
            validation_result["quality_metrics"]["boilerplate_ratio"] = boilerplate_ratio

        return validation_result

    def health_check(self) -> bool:
        """
        Check if the text extraction service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Test with a simple markdown snippet
            test_content = "# Test\n\nThis is a test."
            extracted = self._markdown_to_text(test_content)
            return "Test" in extracted and "test" in extracted
        except Exception:
            return False