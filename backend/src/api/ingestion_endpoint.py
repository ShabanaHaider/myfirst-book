"""
API endpoint for ingestion with /ingest POST route.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any, Optional
import time
import asyncio
from pydantic import BaseModel, Field
from src.services.ingestion_pipeline import IngestionPipelineService
from src.utils.logging import StructuredLogger, log_api_call
from src.config.settings import settings
from src.exceptions import DocumentProcessingError


# Define request and response models
class IngestRequest(BaseModel):
    source_directory: str = Field(
        default=settings.DOCS_DIRECTORY,
        description="Directory containing markdown files to process"
    )
    target_directory: Optional[str] = Field(
        default=None,
        description="Directory to save processed chunks (optional, defaults to configured location)"
    )
    force_reprocess: bool = Field(
        default=False,
        description="Whether to reprocess all files even if unchanged"
    )
    max_concurrent_files: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of files to process concurrently"
    )


class IngestResponse(BaseModel):
    job_id: str
    status: str
    job_id: str
    files_found: int
    files_to_process: int
    estimated_duration_seconds: Optional[float] = None


class IngestionStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Dict[str, Any]
    summary: Dict[str, Any]


# Initialize router and services
router = APIRouter(prefix="/api/v1", tags=["ingestion"])
ingestion_service = IngestionPipelineService()
logger = StructuredLogger("ingestion_api")


@router.post("/ingest", response_model=IngestResponse, summary="Trigger document ingestion process")
async def ingest_documents(request: IngestRequest, background_tasks: BackgroundTasks) -> IngestResponse:
    """
    Trigger the document ingestion process for all markdown files.

    This endpoint starts an asynchronous ingestion job that processes
    markdown files from the specified directory, extracts content,
    chunks it appropriately, and prepares it for embedding.
    """
    start_time = time.time()
    job_id = __import__('uuid').uuid4().hex[:8]  # Simple job ID for tracking

    try:
        # Validate the ingestion configuration
        is_valid, issues = ingestion_service.validate_ingestion_config(request.source_directory)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid ingestion config: {'; '.join(issues)}")

        # Get list of files to process
        from src.services.file_traversal import FileTraversalService
        file_traversal = FileTraversalService()
        all_markdown_files = file_traversal.get_markdown_files(request.source_directory)

        # If not forcing reprocess, determine which files have changed
        if not request.force_reprocess:
            from src.processing.change_detector import ChangeDetector
            change_detector = ChangeDetector()
            changes = change_detector.detect_changes_in_directory(request.source_directory)
            files_to_process = [
                f for f in all_markdown_files
                if changes.get(f, (True, None))[0]  # Only files that have changed
            ]
        else:
            files_to_process = all_markdown_files

        # Start the ingestion job in the background
        background_tasks.add_task(
            _run_ingestion_job,
            job_id,
            request.source_directory,
            request.target_directory,
            request.force_reprocess,
            request.max_concurrent_files
        )

        # Calculate estimated duration (very rough estimation)
        # Assuming ~5 seconds per file as a baseline
        estimated_duration = len(files_to_process) * 5 if files_to_process else 10

        response = IngestResponse(
            job_id=job_id,
            status="processing",
            files_found=len(all_markdown_files),
            files_to_process=len(files_to_process),
            estimated_duration_seconds=estimated_duration
        )

        # Log the API call
        log_api_call(
            operation="ingest_documents",
            status="success",
            duration_ms=(time.time() - start_time) * 1000,
            job_id=job_id,
            files_to_process=len(files_to_process)
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except DocumentProcessingError as e:
        response_time = (time.time() - start_time) * 1000
        logger.error("Document processing failed", job_id=job_id, error=str(e))
        log_api_call(
            operation="ingest_documents",
            status="document_processing_error",
            duration_ms=response_time,
            job_id=job_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error("Ingestion request failed", job_id=job_id, error=str(e))
        log_api_call(
            operation="ingest_documents",
            status="error",
            duration_ms=response_time,
            job_id=job_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Ingestion request failed: {str(e)}")


@router.get("/ingest/status/{job_id}", response_model=IngestionStatusResponse, summary="Check ingestion status")
async def get_ingestion_status(job_id: str) -> IngestionStatusResponse:
    """
    Check the status of an ingestion job.

    This endpoint returns the current status of an ingestion job,
    including progress information and completion statistics.
    """
    start_time = time.time()

    try:
        status = ingestion_service.get_job_status(job_id)

        if status is None:
            # Job not found or already completed
            raise HTTPException(status_code=404, detail=f"Ingestion job {job_id} not found or already completed")

        # Log the API call
        log_api_call(
            operation="get_ingestion_status",
            status="success",
            duration_ms=(time.time() - start_time) * 1000,
            job_id=job_id
        )

        return IngestionStatusResponse(
            job_id=job_id,
            status=status["status"],
            progress=status["progress"],
            summary=status["summary"]
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error("Failed to get ingestion status", job_id=job_id, error=str(e))
        log_api_call(
            operation="get_ingestion_status",
            status="error",
            duration_ms=response_time,
            job_id=job_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to get ingestion status: {str(e)}")


@router.post("/ingest/validate", summary="Validate ingestion configuration")
async def validate_ingestion_config(request: IngestRequest) -> Dict[str, Any]:
    """
    Validate the ingestion configuration before running the pipeline.
    """
    try:
        is_valid, issues = ingestion_service.validate_ingestion_config(request.source_directory)
        return {
            "is_valid": is_valid,
            "issues": issues,
            "source_directory": request.source_directory,
            "config_valid": is_valid
        }
    except Exception as e:
        logger.error("Ingestion config validation failed", source_directory=request.source_directory, error=str(e))
        raise HTTPException(status_code=500, detail=f"Config validation failed: {str(e)}")


@router.get("/ingest/stats", summary="Get ingestion statistics")
async def get_ingestion_stats() -> Dict[str, Any]:
    """
    Get statistics about the ingestion service.
    """
    try:
        stats = ingestion_service.get_ingestion_statistics()
        return stats
    except Exception as e:
        logger.error("Failed to get ingestion stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# Background task function to run the ingestion job
async def _run_ingestion_job(
    job_id: str,
    source_directory: str,
    target_directory: Optional[str],
    force_reprocess: bool,
    max_concurrent_files: int
):
    """
    Background task to run the ingestion job.

    Args:
        job_id: The job ID for tracking
        source_directory: Directory containing markdown files to process
        target_directory: Directory to save processed chunks
        force_reprocess: Whether to reprocess all files
        max_concurrent_files: Maximum concurrent file processing
    """
    try:
        result = await ingestion_service.run_ingestion_pipeline(
            source_directory=source_directory,
            target_directory=target_directory,
            force_reprocess=force_reprocess,
            max_concurrent_files=max_concurrent_files
        )
        logger.info("Ingestion job completed", job_id=job_id, result=result)
    except Exception as e:
        logger.error("Ingestion job failed", job_id=job_id, error=str(e))


# Health check for the ingestion service
@router.get("/health", summary="Check health of the ingestion service")
async def ingestion_health_check() -> Dict[str, bool]:
    """
    Check if the ingestion service and its dependencies are healthy.
    """
    try:
        is_healthy = ingestion_service.health_check()
        return {
            "ingestion_service": is_healthy
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "ingestion_service": False,
            "error": str(e)
        }