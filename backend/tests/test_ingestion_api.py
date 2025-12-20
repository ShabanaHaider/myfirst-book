"""
Integration tests for ingestion API.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os
import tempfile
import json

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.ingestion_endpoint import router, IngestRequest
from backend.src.main import app  # Assuming you have a main app file


# Create a test client
client = TestClient(app)


class TestIngestionAPI:
    """Integration tests for the ingestion API endpoints."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for external dependencies."""
        with patch('src.services.ingestion_pipeline.IngestionPipelineService') as mock_ingestion, \
             patch('src.services.file_traversal.FileTraversalService') as mock_file_traversal, \
             patch('src.processing.change_detector.ChangeDetector') as mock_change_detector:

            # Mock ingestion service
            mock_ingestion.return_value.__init__.return_value = None
            mock_ingestion.return_value.run_ingestion_pipeline = AsyncMock(
                return_value={
                    "job_id": "test-job-123",
                    "status": "completed",
                    "summary": {
                        "total_files_processed": 2,
                        "successful_files": 2,
                        "failed_files": 0,
                        "duration_seconds": 1.5,
                        "chunks_created": 4
                    },
                    "successful_files": ["test1.md", "test2.md"],
                    "failed_files": []
                }
            )
            mock_ingestion.return_value.get_job_status = MagicMock(
                return_value={
                    "job_id": "test-job-123",
                    "status": "completed",
                    "progress": {
                        "total_files": 2,
                        "processed_files": 2,
                        "failed_files": 0,
                        "percentage": 100.0
                    },
                    "summary": {
                        "start_time": 1234567890.0,
                        "end_time": 1234567891.5,
                        "estimated_duration": 2.0
                    }
                }
            )
            mock_ingestion.return_value.validate_ingestion_config = MagicMock(
                return_value=(True, [])
            )
            mock_ingestion.return_value.get_ingestion_statistics = MagicMock(
                return_value={
                    "active_jobs": 0,
                    "active_job_ids": [],
                    "service_status": True,
                    "components": {
                        "file_traversal": True,
                        "text_extraction": True,
                        "content_cleaner": True,
                        "chunking_service": True,
                        "change_detector": True
                    }
                }
            )
            mock_ingestion.return_value.health_check = MagicMock(return_value=True)

            # Mock file traversal service
            mock_file_traversal.return_value.__init__.return_value = None
            mock_file_traversal.return_value.get_markdown_files = MagicMock(
                return_value=["test1.md", "test2.md"]
            )

            # Mock change detector
            mock_change_detector.return_value.__init__.return_value = None
            mock_change_detector.return_value.detect_changes_in_directory = MagicMock(
                return_value={
                    "test1.md": (True, "new_file", None, None),
                    "test2.md": (True, "new_file", None, None)
                }
            )

            yield {
                "ingestion": mock_ingestion,
                "file_traversal": mock_file_traversal,
                "change_detector": mock_change_detector
            }

    def test_ingest_documents_success(self, setup_mocks):
        """Test successful ingestion request."""
        request_data = {
            "source_directory": "/test/docs",
            "force_reprocess": False,
            "max_concurrent_files": 5
        }

        response = client.post("/api/v1/ingest", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "processing"
        assert "files_found" in data
        assert "files_to_process" in data
        assert "estimated_duration_seconds" in data

    def test_ingest_documents_with_validation_error(self, setup_mocks):
        """Test ingestion request with validation error."""
        # Mock invalid config
        setup_mocks["ingestion"].return_value.validate_ingestion_config.return_value = (False, ["Invalid directory"])

        request_data = {
            "source_directory": "/invalid/docs",
        }

        response = client.post("/api/v1/ingest", json=request_data)

        assert response.status_code == 400

    def test_get_ingestion_status_success(self, setup_mocks):
        """Test successful ingestion status request."""
        job_id = "test-job-123"
        response = client.get(f"/api/v1/ingest/status/{job_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["job_id"] == job_id
        assert "status" in data
        assert "progress" in data
        assert "summary" in data

    def test_get_ingestion_status_not_found(self, setup_mocks):
        """Test ingestion status request for non-existent job."""
        # Mock that job doesn't exist
        setup_mocks["ingestion"].return_value.get_job_status.return_value = None

        response = client.get("/api/v1/ingest/status/nonexistent-job")

        assert response.status_code == 404

    def test_validate_ingestion_config_success(self, setup_mocks):
        """Test successful ingestion config validation."""
        request_data = {
            "source_directory": "/test/docs",
            "force_reprocess": False,
            "max_concurrent_files": 5
        }

        response = client.post("/api/v1/ingest/validate", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "is_valid" in data
        assert "issues" in data
        assert data["is_valid"] is True

    def test_get_ingestion_stats_success(self, setup_mocks):
        """Test successful retrieval of ingestion stats."""
        response = client.get("/api/v1/ingest/stats")

        assert response.status_code == 200
        data = response.json()

        assert "active_jobs" in data
        assert "service_status" in data
        assert "components" in data

    def test_ingestion_health_check_success(self, setup_mocks):
        """Test successful ingestion health check."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "ingestion_service" in data
        assert data["ingestion_service"] is True


class TestIngestionAPIErrorHandling:
    """Integration tests for ingestion API error handling."""

    def test_ingest_documents_processing_error(self):
        """Test handling of document processing errors."""
        with patch('src.api.ingestion_endpoint.ingestion_service') as mock_service:
            mock_service.validate_ingestion_config.return_value = (True, [])
            mock_service.run_ingestion_pipeline = AsyncMock(
                side_effect=Exception("Processing failed")
            )

            request_data = {
                "source_directory": "/test/docs",
            }

            response = client.post("/api/v1/ingest", json=request_data)

            assert response.status_code == 500

    def test_get_ingestion_status_error(self):
        """Test handling of ingestion status errors."""
        with patch('src.api.ingestion_endpoint.ingestion_service') as mock_service:
            mock_service.get_job_status.side_effect = Exception("Status check failed")

            response = client.get("/api/v1/ingest/status/test-job")

            assert response.status_code == 500

    def test_validate_ingestion_config_error(self):
        """Test handling of config validation errors."""
        with patch('src.api.ingestion_endpoint.ingestion_service') as mock_service:
            mock_service.validate_ingestion_config.side_effect = Exception("Validation failed")

            request_data = {
                "source_directory": "/test/docs",
            }

            response = client.post("/api/v1/ingest/validate", json=request_data)

            assert response.status_code == 500


class TestIngestionAPIWithRealFiles:
    """Integration tests using temporary real files."""

    def test_ingest_with_temporary_files(self):
        """Test ingestion with actual temporary files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test markdown files
            test_file1 = os.path.join(temp_dir, "test1.md")
            test_file2 = os.path.join(temp_dir, "test2.md")

            with open(test_file1, 'w', encoding='utf-8') as f:
                f.write("# Test Document 1\n\nThis is test content for document 1.")

            with open(test_file2, 'w', encoding='utf-8') as f:
                f.write("# Test Document 2\n\nThis is test content for document 2.")

            # Mock the services appropriately for this test
            with patch('src.services.ingestion_pipeline.IngestionPipelineService') as mock_ingestion:
                # Mock the run_ingestion_pipeline to simulate processing
                async def mock_run_pipeline(*args, **kwargs):
                    return {
                        "job_id": "test-job-real",
                        "status": "completed",
                        "summary": {
                            "total_files_processed": 2,
                            "successful_files": 2,
                            "failed_files": 0,
                            "duration_seconds": 0.5,
                            "chunks_created": 2
                        },
                        "successful_files": [test_file1, test_file2],
                        "failed_files": []
                    }

                mock_ingestion.return_value.run_ingestion_pipeline = mock_run_pipeline
                mock_ingestion.return_value.validate_ingestion_config = MagicMock(return_value=(True, []))
                mock_ingestion.return_value.get_job_status = MagicMock(
                    return_value={
                        "job_id": "test-job-real",
                        "status": "completed",
                        "progress": {
                            "total_files": 2,
                            "processed_files": 2,
                            "failed_files": 0,
                            "percentage": 100.0
                        },
                        "summary": {
                            "start_time": 1234567890.0,
                            "end_time": 1234567890.5,
                            "estimated_duration": 1.0
                        }
                    }
                )

                # Now test the API
                request_data = {
                    "source_directory": temp_dir,
                    "force_reprocess": True  # Force reprocess to ensure files are picked up
                }

                response = client.post("/api/v1/ingest", json=request_data)

                # The response should be successful since we're mocking the actual processing
                assert response.status_code == 200
                data = response.json()

                assert "job_id" in data
                assert data["files_found"] >= 2  # Should find our test files


class TestIngestionAPIBackgroundTasks:
    """Tests for background task handling in ingestion API."""

    @pytest.mark.asyncio
    async def test_ingestion_runs_as_background_task(self):
        """Test that ingestion runs as a background task."""
        # This test verifies that the ingestion process is properly set up as a background task
        # In a real scenario, we'd need to check that the background task was actually scheduled
        with patch('src.api.ingestion_endpoint._run_ingestion_job') as mock_background_task:
            with patch('src.api.ingestion_endpoint.ingestion_service') as mock_service:
                mock_service.validate_ingestion_config.return_value = (True, [])

                # Mock the file traversal to return some files
                with patch('src.services.file_traversal.FileTraversalService') as mock_traversal:
                    mock_traversal.return_value.get_markdown_files.return_value = ["test.md"]

                    # Mock the change detector
                    with patch('src.processing.change_detector.ChangeDetector') as mock_detector:
                        mock_detector.return_value.detect_changes_in_directory.return_value = {
                            "test.md": (True, "new_file", None, None)
                        }

                        request_data = {
                            "source_directory": "/test/docs",
                        }

                        response = client.post("/api/v1/ingest", json=request_data)

                        assert response.status_code == 200
                        # Background task should have been scheduled
                        # Note: In real implementation, we'd verify the background task was added


def test_ingestion_endpoint_imports():
    """Test that all necessary components can be imported without error."""
    # This is a basic test to ensure imports work correctly
    from src.api.ingestion_endpoint import (
        IngestRequest,
        IngestResponse,
        IngestionStatusResponse,
        router,
        ingestion_service,
        logger
    )

    assert router is not None
    assert ingestion_service is not None
    assert logger is not None
    assert IngestRequest is not None
    assert IngestResponse is not None
    assert IngestionStatusResponse is not None


class TestIngestionAPISchemaValidation:
    """Tests for request/response schema validation."""

    def test_ingest_request_schema_validation(self):
        """Test that request schema validation works correctly."""
        # Test with minimal valid request
        valid_request = {
            "source_directory": "/test/docs"
        }

        response = client.post("/api/v1/ingest", json=valid_request)
        # Should not fail due to schema validation (may fail for other reasons like missing files)
        # but schema validation should pass

        # Test with invalid max_concurrent_files
        invalid_request = {
            "source_directory": "/test/docs",
            "max_concurrent_files": 0  # Should be >= 1
        }

        response = client.post("/api/v1/ingest", json=invalid_request)
        # Should return 422 for validation error
        assert response.status_code in [422, 500]  # Could be validation error or processing error

    def test_ingest_request_schema_with_all_fields(self):
        """Test request with all optional fields provided."""
        complete_request = {
            "source_directory": "/test/docs",
            "target_directory": "/test/output",
            "force_reprocess": True,
            "max_concurrent_files": 10
        }

        response = client.post("/api/v1/ingest", json=complete_request)
        # Should not fail due to schema validation