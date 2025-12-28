"""
Content cleaning module to remove Docusaurus boilerplate.
"""
import re
from typing import List, Dict, Any, Tuple
from src.utils.text_utils import clean_text, normalize_whitespace, extract_meaningful_content
from src.utils.logging import StructuredLogger, log_ingestion_event
from src.exceptions import DocumentProcessingError


class ContentCleaner:
    """
    Service for cleaning and normalizing content, specifically removing Docusaurus boilerplate.
    """

    def __init__(self):
        """Initialize the content cleaner."""
        self.logger = StructuredLogger("content_cleaner")

    def clean_docusaurus_content(self, content: str) -> Dict[str, Any]:
        """
        Clean content by removing Docusaurus-specific boilerplate.

        Args:
            content: Raw content to clean

        Returns:
            Dictionary with cleaned content and cleaning metadata
        """
        try:
            original_length = len(content)

            # Remove YAML frontmatter
            cleaned_content = self._remove_frontmatter(content)

            # Remove Docusaurus-specific elements
            cleaned_content = self._remove_docusaurus_elements(cleaned_content)

            # Remove navigation elements and other boilerplate
            cleaned_content = self._remove_navigation_boilerplate(cleaned_content)

            # Normalize whitespace
            cleaned_content = normalize_whitespace(cleaned_content)

            # Remove low-value content
            cleaned_content = self._remove_low_value_content(cleaned_content)

            # Clean up any remaining artifacts
            cleaned_content = clean_text(cleaned_content)

            # Create cleaning metadata
            cleaning_metadata = {
                "original_length": original_length,
                "cleaned_length": len(cleaned_content),
                "reduction_percentage": (1 - len(cleaned_content) / original_length) * 100 if original_length > 0 else 0,
                "cleaning_steps": [
                    "frontmatter_removal",
                    "docusaurus_elements_removal",
                    "navigation_boilerplate_removal",
                    "whitespace_normalization",
                    "low_value_content_removal",
                    "text_cleaning"
                ]
            }

            result = {
                "original_content": content,
                "cleaned_content": cleaned_content,
                "cleaning_metadata": cleaning_metadata
            }

            log_ingestion_event(
                event="content_cleaning_success",
                file_path="unknown",  # Will be set by caller
                status="success",
                original_length=original_length,
                cleaned_length=len(cleaned_content)
            )

            return result

        except Exception as e:
            self.logger.error("Failed to clean Docusaurus content", error=str(e))
            log_ingestion_event(
                event="content_cleaning_failed",
                file_path="unknown",
                status="error",
                error=str(e)
            )
            raise DocumentProcessingError(f"Failed to clean content: {str(e)}")

    def _remove_frontmatter(self, content: str) -> str:
        """
        Remove YAML frontmatter from content.

        Args:
            content: Content that may contain frontmatter

        Returns:
            Content with frontmatter removed
        """
        # Pattern for YAML frontmatter: ---\n...content...\n---
        frontmatter_pattern = r'^---\n.*?\n---\n?'
        cleaned_content = re.sub(frontmatter_pattern, '', content, flags=re.DOTALL)
        return cleaned_content

    def _remove_docusaurus_elements(self, content: str) -> str:
        """
        Remove Docusaurus-specific elements like import statements, JSX components, etc.

        Args:
            content: Content to clean

        Returns:
            Content with Docusaurus elements removed
        """
        # Remove import statements
        content = re.sub(r'^import.*$', '', content, flags=re.MULTILINE)

        # Remove export statements
        content = re.sub(r'^export.*$', '', content, flags=re.MULTILINE)

        # Remove JSX-like components (simple approach - just remove lines that look like JSX)
        jsx_patterns = [
            r'<\w+.*?>.*?</\w+>',  # Self-closing and paired tags
            r'<\w+.*?/>',           # Self-closing tags
            r'{[^}]*import[^}]*}',  # Template placeholders with imports
        ]

        for pattern in jsx_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL)

        # Remove Docusaurus-specific directives
        content = re.sub(r':::.*?:::', '', content, flags=re.DOTALL)  # Admonitions

        return content

    def _remove_navigation_boilerplate(self, content: str) -> str:
        """
        Remove navigation elements and other boilerplate content.

        Args:
            content: Content to clean

        Returns:
            Content with navigation elements removed
        """
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            # Skip lines that are clearly navigation or boilerplate
            stripped_line = line.strip().lower()

            # Skip common navigation elements
            if any(skip_text in stripped_line for skip_text in [
                '{/*',
                '*/}',
                'sidebar',
                'navbar',
                'footer',
                'table of contents',
                'toc',
                'previous:',
                'next:',
                '« ',
                ' »',
                'previous',
                'next',
                'back to top',
                'return to',
                'go back',
            ]):
                continue

            # Skip lines that look like navigation links
            if re.match(r'^\s*-\s*\[.*\]\(.*\)\s*$', line):  # Markdown links in lists
                continue

            # Skip lines that look like table of contents entries
            if re.match(r'^\s*[*+-]\s+#+\s+.*', line):  # List items with headers
                continue

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _remove_low_value_content(self, content: str) -> str:
        """
        Remove low-value content like tables of contents, repeated navigation, etc.

        Args:
            content: Content to clean

        Returns:
            Content with low-value elements removed
        """
        lines = content.split('\n')
        cleaned_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped_line = line.strip()

            # Check if this line and surrounding lines form a table of contents pattern
            is_toc = False

            # Look for patterns that indicate table of contents
            if re.match(r'^\s*[*+-]\s+\[.*\]\(.*\)', line):  # List with links
                is_toc = True
            elif re.match(r'^\d+\.\s+\[.*\]\(.*\)', line):  # Numbered list with links
                is_toc = True
            elif stripped_line.lower().startswith('contents') or stripped_line.lower().startswith('table of contents'):
                is_toc = True

            if not is_toc:
                cleaned_lines.append(line)

            i += 1

        return '\n'.join(cleaned_lines)

    def remove_duplicate_content(self, content: str) -> str:
        """
        Remove duplicate content from text.

        Args:
            content: Content to deduplicate

        Returns:
            Content with duplicates removed
        """
        lines = content.split('\n')
        seen_lines = set()
        unique_lines = []

        for line in lines:
            # Normalize the line for comparison
            normalized_line = line.strip().lower()

            # Skip empty lines and already seen lines
            if normalized_line and normalized_line not in seen_lines:
                seen_lines.add(normalized_line)
                unique_lines.append(line)

        return '\n'.join(unique_lines)

    def clean_and_validate_chunk(self, text_chunk: str, min_word_count: int = 5) -> Tuple[str, bool, List[str]]:
        """
        Clean and validate a text chunk.

        Args:
            text_chunk: The text chunk to clean and validate
            min_word_count: Minimum number of words required for content to be meaningful

        Returns:
            Tuple of (cleaned_chunk, is_valid, issues_found)
        """
        issues = []

        # Clean the chunk
        cleaned_chunk = clean_text(text_chunk)
        cleaned_chunk = normalize_whitespace(cleaned_chunk)

        # Validate meaningful content
        meaningful_content = extract_meaningful_content(cleaned_chunk, min_word_count)
        if not meaningful_content:
            issues.append(f"Content has fewer than {min_word_count} words")
            return cleaned_chunk, False, issues

        # Check for excessive special characters
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s]', meaningful_content)) / len(meaningful_content)
        if special_char_ratio > 0.5:  # More than 50% special characters
            issues.append("Content has excessive special characters")

        # Check for repeated characters (indicating potential artifacts)
        if re.search(r'(.)\1{10,}', meaningful_content):  # Same character repeated 10+ times
            issues.append("Content has repeated character sequences")

        is_valid = len(issues) == 0
        return meaningful_content, is_valid, issues

    def identify_boilerplate_patterns(self, content: str) -> List[Dict[str, Any]]:
        """
        Identify potential boilerplate patterns in content.

        Args:
            content: Content to analyze

        Returns:
            List of identified boilerplate patterns
        """
        boilerplate_patterns = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            pattern_found = None

            # Check for common boilerplate patterns
            if re.match(r'^\s*[*+-]\s+\[.*\]\(.*\)', line):
                pattern_found = {
                    "line_number": i,
                    "type": "navigation_list",
                    "content": line.strip(),
                    "description": "Navigation or table of contents list item"
                }
            elif re.match(r'^\s*import\s+.*', line):
                pattern_found = {
                    "line_number": i,
                    "type": "import_statement",
                    "content": line.strip(),
                    "description": "Import statement"
                }
            elif re.match(r'^\s*export\s+.*', line):
                pattern_found = {
                    "line_number": i,
                    "type": "export_statement",
                    "content": line.strip(),
                    "description": "Export statement"
                }
            elif re.match(r'^\s*<\w+.*?>', line):
                pattern_found = {
                    "line_number": i,
                    "type": "jsx_element",
                    "content": line.strip(),
                    "description": "JSX element"
                }

            if pattern_found:
                boilerplate_patterns.append(pattern_found)

        return boilerplate_patterns

    def clean_content_batch(self, contents: List[str]) -> List[Dict[str, Any]]:
        """
        Clean multiple content items in a batch.

        Args:
            contents: List of content strings to clean

        Returns:
            List of dictionaries with cleaned content and metadata
        """
        results = []
        successful = 0
        failed = 0

        for content in contents:
            try:
                result = self.clean_docusaurus_content(content)
                result['success'] = True
                results.append(result)
                successful += 1
            except Exception as e:
                self.logger.error("Failed to clean content in batch", error=str(e))
                results.append({
                    "original_content": content,
                    "cleaned_content": "",
                    "cleaning_metadata": {},
                    "success": False,
                    "error": str(e)
                })
                failed += 1

        self.logger.info(
            "Batch content cleaning completed",
            total_items=len(contents),
            successful=successful,
            failed=failed
        )

        return results

    def remove_duplicate_blocks(self, content: str) -> str:
        """
        Remove duplicate blocks of content.

        Args:
            content: Content to deduplicate

        Returns:
            Content with duplicate blocks removed
        """
        lines = content.split('\n')
        seen_blocks = set()
        unique_lines = []
        current_block = []

        for line in lines:
            stripped_line = line.strip()

            # If line is empty or we encounter a header, consider it a block boundary
            if not stripped_line or line.startswith(('#', '##', '###', '####', '#####', '######')):
                # Process the current block
                if current_block:
                    block_text = '\n'.join(current_block)
                    block_hash = hash(block_text.lower().strip())

                    if block_hash not in seen_blocks:
                        seen_blocks.add(block_hash)
                        unique_lines.extend(current_block)

                    current_block = []

                # Add the header line
                if stripped_line and stripped_line.startswith(('#', '##', '###', '####', '#####', '######')):
                    unique_lines.append(line)
            else:
                current_block.append(line)

        # Process the last block if it exists
        if current_block:
            block_text = '\n'.join(current_block)
            block_hash = hash(block_text.lower().strip())

            if block_hash not in seen_blocks:
                seen_blocks.add(block_hash)
                unique_lines.extend(current_block)

        return '\n'.join(unique_lines)

    def health_check(self) -> bool:
        """
        Check if the content cleaner is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Test with a sample content containing various elements to clean
            test_content = """---
title: Test Page
sidebar_label: Test
---

import Component from '@docusaurus/Component';

# Test Header

This is meaningful content.

- [Navigation Link](/link)
- [Another Link](/another)

<Component />

:::note
This is a note.
:::

End of content.
"""

            result = self.clean_docusaurus_content(test_content)
            # Check that meaningful content remains after cleaning
            return "meaningful content" in result["cleaned_content"].lower()
        except Exception:
            return False