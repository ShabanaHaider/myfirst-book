"""
Unit tests for ingestion functionality.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from src.services.ingestion_pipeline import IngestionPipelineService
from src.services.file_traversal import FileTraversalService
from src.processing.text_extraction import TextExtractionService
from src.processing.content_cleaner import ContentCleaner
from src.services.chunking_service import ChunkingService
from src.processing.change_detector import ChangeDetector
from src.processing.chunk_persistence import ChunkPersistenceService
from src.models.document_chunk import DocumentChunk
from datetime import datetime


@pytest.fixture
def ingestion_service():
    """Fixture to create an IngestionPipelineService instance."""
    service = IngestionPipelineService()
    yield service


@pytest.fixture
def mock_file_traversal():
    """Fixture to mock the file traversal service."""
    with patch('src.services.ingestion_pipeline.FileTraversalService') as mock:
        instance = mock.return_value
        instance.get_markdown_files.return_value = ["test1.md", "test2.md"]
        yield instance


@pytest.fixture
def mock_text_extraction():
    """Fixture to mock the text extraction service."""
    with patch('src.services.ingestion_pipeline.TextExtractionService') as mock:
        instance = mock.return_value
        instance.extract_text_from_markdown.return_value = {
            "extracted_text": "Sample text content",
            "extraction_metadata": {}
        }
        yield instance


@pytest.fixture
def mock_content_cleaner():
    """Fixture to mock the content cleaner service."""
    with patch('src.services.ingestion_pipeline.ContentCleaner') as mock:
        instance = mock.return_value
        instance.clean_docusaurus_content.return_value = {
            "cleaned_content": "Cleaned text content",
            "cleaning_metadata": {}
        }
        yield instance


@pytest.fixture
def mock_chunking_service():
    """Fixture to mock the chunking service."""
    with patch('src.services.ingestion_pipeline.ChunkingService') as mock:
        instance = mock.return_value
        # Create a sample chunk for testing
        sample_chunk = DocumentChunk(
            id="test-chunk-id",
            text_content="Sample chunk content",
            source_file_path="test.md",
            chunk_index=0,
            character_position=0,
            content_hash="test-hash",
            created_at=datetime.now()
        )
        instance.create_chunks.return_value = [sample_chunk]
        instance.validate_chunks.return_value = {
            "total_chunks": 1,
            "valid_chunks": 1,
            "invalid_chunks": 0,
            "issues": [],
            "validation_details": [{"chunk_index": 0, "is_valid": True, "issues": []}]
        }
        yield instance


class TestIngestionPipelineService:
    """Unit tests for IngestionPipelineService."""

    @pytest.mark.asyncio
    async def test_run_ingestion_pipeline_success(
        self,
        ingestion_service,
        mock_file_traversal,
        mock_text_extraction,
        mock_content_cleaner,
        mock_chunking_service
    ):
        """Test successful ingestion pipeline run."""
        # Mock the change detector
        with patch.object(ingestion_service, 'change_detector') as mock_change_detector:
            mock_change_detector.detect_changes_in_directory.return_value = {
                "test1.md": (True, "new_file", None, None),
                "test2.md": (True, "new_file", None, None)
            }

            # Mock the chunk persistence
            with patch('src.services.ingestion_pipeline.ChunkPersistenceService') as mock_persistence:
                mock_persistence.return_value.save_chunks.return_value = {
                    "total_chunks": 2,
                    "successful_saves": 2,
                    "failed_saves": 0
                }

                result = await ingestion_service.run_ingestion_pipeline(
                    source_directory="test_dir",
                    max_concurrent_files=2
                )

                assert "job_id" in result
                assert result["status"] == "completed"
                assert result["summary"]["successful_files"] == 2
                assert result["summary"]["failed_files"] == 0

    @pytest.mark.asyncio
    async def test_run_ingestion_pipeline_with_force_reprocess(
        self,
        ingestion_service,
        mock_file_traversal,
        mock_text_extraction,
        mock_content_cleaner,
        mock_chunking_service
    ):
        """Test ingestion pipeline with force reprocess."""
        with patch.object(ingestion_service, 'change_detector') as mock_change_detector:
            # Mock change detector to return all files as changed when force_reprocess=True
            mock_change_detector.detect_changes_in_directory.return_value = {
                "test1.md": (True, "content_changed", None, None),
                "test2.md": (True, "content_changed", None, None)
            }

            with patch('src.services.ingestion_pipeline.ChunkPersistenceService') as mock_persistence:
                mock_persistence.return_value.save_chunks.return_value = {
                    "total_chunks": 2,
                    "successful_saves": 2,
                    "failed_saves": 0
                }

                result = await ingestion_service.run_ingestion_pipeline(
                    source_directory="test_dir",
                    force_reprocess=True
                )

                assert result["status"] == "completed"
                # Should process all files when force_reprocess=True
                assert result["summary"]["total_files_processed"] == 2

    @pytest.mark.asyncio
    async def test_run_incremental_ingestion(
        self,
        ingestion_service,
        mock_file_traversal,
        mock_text_extraction,
        mock_content_cleaner,
        mock_chunking_service
    ):
        """Test incremental ingestion functionality."""
        with patch.object(ingestion_service, 'change_detector') as mock_change_detector:
            # Mock to return only one file as changed
            mock_change_detector.detect_changes_in_directory.return_value = {
                "test1.md": (True, "content_changed", None, None),
                "test2.md": (False, "no_change", None, None)  # This should be skipped
            }

            with patch('src.services.ingestion_pipeline.ChunkPersistenceService') as mock_persistence:
                mock_persistence.return_value.save_chunks.return_value = {
                    "total_chunks": 1,
                    "successful_saves": 1,
                    "failed_saves": 0
                }

                result = await ingestion_service.run_incremental_ingestion(
                    source_directory="test_dir"
                )

                assert result["status"] == "completed"
                # Should only process the changed file
                assert result["summary"]["total_files_processed"] == 1

    def test_get_job_status_active_job(self, ingestion_service):
        """Test getting status for an active job."""
        # Create a mock job
        from src.services.ingestion_pipeline import IngestionJob
        job = IngestionJob(
            job_id="test-job",
            status="processing",
            total_files=10,
            processed_files=5,
            failed_files=1,
            start_time=1234567890.0,
            progress_percentage=50.0
        )
        ingestion_service.active_jobs["test-job"] = job

        status = ingestion_service.get_job_status("test-job")
        assert status is not None
        assert status["job_id"] == "test-job"
        assert status["status"] == "processing"
        assert status["progress"]["percentage"] == 50.0

    def test_get_job_status_nonexistent_job(self, ingestion_service):
        """Test getting status for a nonexistent job."""
        status = ingestion_service.get_job_status("nonexistent-job")
        assert status is None

    def test_validate_ingestion_config_valid(self, ingestion_service, mock_file_traversal):
        """Test validation of a valid ingestion configuration."""
        is_valid, issues = ingestion_service.validate_ingestion_config("valid_dir")
        assert is_valid is True
        assert len(issues) == 0

    def test_validate_ingestion_config_invalid_directory(self, ingestion_service):
        """Test validation of an invalid directory."""
        # Mock the file traversal to simulate directory access issues
        with patch.object(ingestion_service.file_traversal, 'get_markdown_files') as mock_get_files:
            mock_get_files.side_effect = Exception("Directory does not exist")

            is_valid, issues = ingestion_service.validate_ingestion_config("invalid_dir")
            assert is_valid is False
            assert len(issues) > 0

    def test_get_ingestion_statistics(self, ingestion_service):
        """Test getting ingestion statistics."""
        stats = ingestion_service.get_ingestion_statistics()

        assert "active_jobs" in stats
        assert "active_job_ids" in stats
        assert "service_status" in stats
        assert "components" in stats

        # Check that component statuses are boolean
        for component_status in stats["components"].values():
            assert isinstance(component_status, bool)

    @pytest.mark.asyncio
    async def test_process_single_file_success(
        self,
        ingestion_service,
        mock_text_extraction,
        mock_content_cleaner,
        mock_chunking_service
    ):
        """Test successful processing of a single file."""
        with patch('src.services.ingestion_pipeline.ChunkPersistenceService') as mock_persistence:
            mock_persistence.return_value.save_chunks.return_value = {
                "total_chunks": 1,
                "successful_saves": 1,
                "failed_saves": 0
            }

            result = await ingestion_service._process_single_file("test.md", "/tmp")

            assert result["file_path"] == "test.md"
            assert result["success"] is True
            assert "chunks" in result
            assert len(result["chunks"]) == 1

    @pytest.mark.asyncio
    async def test_process_single_file_failure(
        self,
        ingestion_service
    ):
        """Test processing of a single file that fails."""
        # Mock text extraction to raise an exception
        with patch.object(ingestion_service.text_extraction, 'extract_text_from_markdown') as mock_extract:
            mock_extract.side_effect = Exception("Extraction failed")

            result = await ingestion_service._process_single_file("test.md", "/tmp")

            assert result["file_path"] == "test.md"
            assert result["success"] is False
            assert "error" in result


class TestFileTraversalService:
    """Unit tests for FileTraversalService."""

    def test_get_markdown_files(self, tmp_path):
        """Test getting markdown files from a directory."""
        # Create test files
        (tmp_path / "doc1.md").write_text("# Document 1")
        (tmp_path / "doc2.markdown").write_text("# Document 2")
        (tmp_path / "not_markdown.txt").write_text("Not markdown")

        service = FileTraversalService()
        files = service.get_markdown_files(str(tmp_path))

        assert len(files) == 2
        assert any("doc1.md" in f for f in files)
        assert any("doc2.markdown" in f for f in files)

    def test_get_markdown_files_nonexistent_dir(self):
        """Test getting markdown files from a nonexistent directory."""
        service = FileTraversalService()
        with pytest.raises(Exception):  # Should raise FileOperationError
            service.get_markdown_files("/nonexistent/directory")


class TestTextExtractionService:
    """Unit tests for TextExtractionService."""

    def test_extract_text_from_markdown(self, tmp_path):
        """Test extracting text from a markdown file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Header\n\nThis is test content.")

        service = TextExtractionService()
        result = service.extract_text_from_markdown(str(test_file))

        assert "extracted_text" in result
        assert "Test Header" in result["extracted_text"]
        assert "test content" in result["extracted_text"]

    def test_extract_text_from_markdown_with_frontmatter(self, tmp_path):
        """Test extracting text from markdown with frontmatter."""
        test_file = tmp_path / "test.md"
        test_file.write_text("""---
title: Test Page
---

# Test Header

This is test content.
""")

        service = TextExtractionService()
        result = service.extract_text_from_markdown(str(test_file), remove_boilerplate=True)

        assert "extracted_text" in result
        assert "title: Test Page" not in result["extracted_text"].lower()
        assert "Test Header" in result["extracted_text"]
        assert "test content" in result["extracted_text"]


class TestContentCleaner:
    """Unit tests for ContentCleaner."""

    def test_clean_docusaurus_content(self):
        """Test cleaning Docusaurus-specific content."""
        content = """---
title: Test
---

import Component from '@docusaurus/Component';

# Header

This is content.

[Navigation](/nav)
"""

        cleaner = ContentCleaner()
        result = cleaner.clean_docusaurus_content(content)

        assert "title: Test" not in result["cleaned_content"]
        assert "import Component" not in result["cleaned_content"]
        assert "Navigation" not in result["cleaned_content"]
        assert "This is content" in result["cleaned_content"]

    def test_clean_and_validate_chunk_valid(self):
        """Test cleaning and validating a valid chunk."""
        cleaner = ContentCleaner()
        text, is_valid, issues = cleaner.clean_and_validate_chunk("This is a valid chunk with enough words.", min_word_count=5)

        assert is_valid is True
        assert len(issues) == 0
        assert "valid chunk" in text

    def test_clean_and_validate_chunk_invalid(self):
        """Test cleaning and validating an invalid chunk."""
        cleaner = ContentCleaner()
        text, is_valid, issues = cleaner.clean_and_validate_chunk("Hi.", min_word_count=5)

        assert is_valid is False
        assert len(issues) > 0


class TestChunkingService:
    """Unit tests for ChunkingService."""

    def test_create_chunks(self):
        """Test creating chunks from text."""
        service = ChunkingService()
        text = "This is a test sentence. " * 20  # Create text that will be chunked
        chunks = service.create_chunks(text, "test.md", max_tokens=50, min_word_count=3)

        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, DocumentChunk)
            assert len(chunk.text_content) > 0

    def test_validate_chunk_valid(self):
        """Test validating a valid chunk."""
        chunk = DocumentChunk(
            id="test-id",
            text_content="This is a valid chunk with appropriate content.",
            source_file_path="test.md",
            chunk_index=0,
            character_position=0,
            content_hash="test-hash",
            created_at=datetime.now()
        )

        service = ChunkingService()
        is_valid, issues = service.validate_chunk(chunk, max_tokens=512, min_word_count=5)

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_chunk_invalid(self):
        """Test validating an invalid chunk."""
        chunk = DocumentChunk(
            id="",
            text_content="Hi",
            source_file_path="",
            chunk_index=-1,
            character_position=0,
            content_hash="test-hash",
            created_at=datetime.now()
        )

        service = ChunkingService()
        is_valid, issues = service.validate_chunk(chunk, max_tokens=512, min_word_count=5)

        assert is_valid is False
        assert len(issues) > 0


class TestChangeDetector:
    """Unit tests for ChangeDetector."""

    def test_get_file_state(self, tmp_path):
        """Test getting file state."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        detector = ChangeDetector()
        state = detector.get_file_state(str(test_file))

        assert state is not None
        assert state.file_path == str(test_file)
        assert state.size > 0

    def test_has_file_changed_new_file(self, tmp_path):
        """Test detecting change for a new file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        detector = ChangeDetector()
        has_changed, change_type = detector.has_file_changed(str(test_file), previous_state=None)

        assert has_changed is True
        assert change_type == "new_file"

    def test_detect_changes_in_directory(self, tmp_path):
        """Test detecting changes in a directory."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\nContent")

        detector = ChangeDetector()
        changes = detector.detect_changes_in_directory(str(tmp_path), file_extensions=['.md'])

        assert str(test_file) in changes
        has_changed, change_type, prev_state, curr_state = changes[str(test_file)]
        assert has_changed is True  # First time seeing the file
        assert change_type == "new_file"


class TestChunkPersistenceService:
    """Unit tests for ChunkPersistenceService."""

    def test_save_chunk(self, tmp_path):
        """Test saving a chunk."""
        chunk = DocumentChunk(
            id="test-chunk-id",
            text_content="Test chunk content",
            source_file_path="test.md",
            chunk_index=0,
            character_position=0,
            content_hash="test-hash",
            created_at=datetime.now()
        )

        service = ChunkPersistenceService(base_directory=str(tmp_path))
        success = service.save_chunk(chunk)

        assert success is True
        # Verify file was created
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1

    def test_save_chunks(self, tmp_path):
        """Test saving multiple chunks."""
        chunks = [
            DocumentChunk(
                id=f"test-chunk-id-{i}",
                text_content=f"Test chunk content {i}",
                source_file_path=f"test{i}.md",
                chunk_index=i,
                character_position=0,
                content_hash=f"test-hash-{i}",
                created_at=datetime.now()
            )
            for i in range(2)
        ]

        service = ChunkPersistenceService(base_directory=str(tmp_path))
        results = service.save_chunks(chunks)

        assert results["total_chunks"] == 2
        assert results["successful_saves"] == 2
        assert results["failed_saves"] == 0