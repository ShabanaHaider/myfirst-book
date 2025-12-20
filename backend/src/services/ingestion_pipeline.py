"""
Ingestion pipeline service for end-to-end processing.
"""
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from src.services.file_traversal import FileTraversalService
from src.processing.text_extraction import TextExtractionService
from src.processing.content_cleaner import ContentCleaner
from src.services.chunking_service import ChunkingService
from src.processing.change_detector import ChangeDetector
from src.services.embedding_service import EmbeddingService
from src.services.vector_storage import VectorStorageService
from src.models.document_chunk import DocumentChunk
from src.utils.logging import StructuredLogger, log_ingestion_event
from src.utils.file_utils import ensure_directory_exists
from src.config.settings import settings
from src.exceptions import DocumentProcessingError, FileOperationError


@dataclass
class IngestionJob:
    """Represents an ingestion job."""
    job_id: str
    status: str  # pending, processing, completed, failed
    total_files: int
    processed_files: int
    failed_files: int
    start_time: float
    end_time: Optional[float] = None
    estimated_duration: Optional[float] = None
    progress_percentage: float = 0.0


class IngestionPipelineService:
    """
    Service for managing the end-to-end ingestion pipeline.
    """

    def __init__(self):
        """Initialize the ingestion pipeline service."""
        self.logger = StructuredLogger("ingestion_pipeline_service")
        self.file_traversal = FileTraversalService()
        self.text_extraction = TextExtractionService()
        self.content_cleaner = ContentCleaner()
        self.chunking_service = ChunkingService()
        self.change_detector = ChangeDetector()
        self.embedding_service = EmbeddingService()
        self.vector_storage_service = VectorStorageService()
        self.active_jobs: Dict[str, IngestionJob] = {}

    async def run_ingestion_pipeline(
        self,
        source_directory: str,
        target_directory: str = None,
        force_reprocess: bool = False,
        max_concurrent_files: int = 5
    ) -> Dict[str, Any]:
        """
        Run the complete ingestion pipeline.

        Args:
            source_directory: Directory containing markdown files to process
            target_directory: Directory to save processed chunks (defaults to settings.PROCESSED_CHUNKS_DIR)
            force_reprocess: Whether to reprocess all files even if unchanged
            max_concurrent_files: Maximum number of files to process concurrently

        Returns:
            Dictionary with ingestion results
        """
        job_id = __import__('uuid').uuid4().hex[:8]
        start_time = time.time()

        # Create job tracking
        job = IngestionJob(
            job_id=job_id,
            status="processing",
            total_files=0,
            processed_files=0,
            failed_files=0,
            start_time=start_time
        )
        self.active_jobs[job_id] = job

        try:
            # Get markdown files
            self.logger.info("Starting ingestion pipeline", job_id=job_id, source_directory=source_directory)

            markdown_files = self.file_traversal.get_markdown_files(source_directory)
            job.total_files = len(markdown_files)

            # If not forcing reprocess, detect changes
            if not force_reprocess:
                changed_files_map = self.change_detector.detect_changes_in_directory(source_directory)
                markdown_files = [
                    f for f in markdown_files
                    if changed_files_map.get(f, (True, None))[0]  # Only process changed files
                ]
                self.logger.info(
                    "Filtered files based on changes",
                    job_id=job_id,
                    original_count=job.total_files,
                    filtered_count=len(markdown_files)
                )

            # Create target directory if needed
            if target_directory is None:
                target_directory = settings.PROCESSED_CHUNKS_DIR
            ensure_directory_exists(target_directory)

            # Process files with limited concurrency
            semaphore = asyncio.Semaphore(max_concurrent_files)

            async def process_file_wrapper(file_path: str):
                async with semaphore:
                    return await self._process_single_file(file_path, target_directory)

            # Create tasks for all files
            tasks = [process_file_wrapper(file_path) for file_path in markdown_files]

            # Process files with progress tracking
            results = []
            for i, task in enumerate(asyncio.as_completed(tasks)):
                result = await task
                results.append(result)

                # Update job progress
                job.processed_files += 1
                if result.get("success") is False:
                    job.failed_files += 1
                job.progress_percentage = (job.processed_files / job.total_files) * 100

                # Log progress periodically
                if i % max(1, len(markdown_files) // 10) == 0:  # Log every 10%
                    self.logger.info(
                        "Ingestion progress",
                        job_id=job_id,
                        processed=job.processed_files,
                        total=job.total_files,
                        percentage=job.progress_percentage
                    )

            # Count successful and failed files
            successful_files = [r for r in results if r.get("success")]
            failed_files = [r for r in results if not r.get("success")]

            # Calculate duration
            duration = time.time() - start_time
            job.end_time = time.time()
            job.status = "completed"

            # Update change detector with processed files
            processed_paths = [r["file_path"] for r in successful_files]
            self.change_detector.mark_files_as_processed(processed_paths)

            # Collect all chunks from successful files for embedding generation
            all_chunks = []
            for result in successful_files:
                chunks = result.get("chunks", [])
                all_chunks.extend(chunks)

            # Generate embeddings and store in Qdrant if we have chunks
            if all_chunks:
                self.logger.info(f"Generating embeddings for {len(all_chunks)} chunks")

                # Generate embeddings for all chunks
                embedding_vectors = await self.embedding_service.generate_embeddings_for_chunks(all_chunks)

                # Store embeddings in Qdrant
                storage_result = await self.vector_storage_service.validate_and_store_embeddings(embedding_vectors)

                self.logger.info(f"Storage result: {storage_result}")
            else:
                self.logger.info("No chunks to process, skipping embedding generation and storage")

            # Prepare result
            result = {
                "job_id": job_id,
                "status": "completed",
                "summary": {
                    "total_files_processed": len(markdown_files),
                    "successful_files": len(successful_files),
                    "failed_files": len(failed_files),
                    "duration_seconds": duration,
                    "chunks_created": sum(len(r.get("chunks", [])) for r in successful_files)
                },
                "successful_files": [r["file_path"] for r in successful_files],
                "failed_files": [
                    {"file_path": r["file_path"], "error": r.get("error", "Unknown error")}
                    for r in failed_files
                ]
            }

            log_ingestion_event(
                event="ingestion_pipeline_completed",
                file_path=source_directory,
                status="success",
                processed_files=len(successful_files),
                failed_files=len(failed_files),
                duration_seconds=duration
            )

            return result

        except Exception as e:
            job.status = "failed"
            job.end_time = time.time()
            self.logger.error("Ingestion pipeline failed", job_id=job_id, error=str(e))
            log_ingestion_event(
                event="ingestion_pipeline_failed",
                file_path=source_directory,
                status="error",
                error=str(e)
            )
            raise DocumentProcessingError(f"Ingestion pipeline failed: {str(e)}")
        finally:
            # Clean up job from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

    async def _process_single_file(self, file_path: str, target_directory: str) -> Dict[str, Any]:
        """
        Process a single file through the ingestion pipeline.

        Args:
            file_path: Path to the file to process
            target_directory: Directory to save processed chunks

        Returns:
            Dictionary with processing results
        """
        try:
            # Extract text from markdown
            extraction_result = self.text_extraction.extract_text_from_markdown(file_path)
            raw_text = extraction_result["extracted_text"]

            # Clean the content
            cleaning_result = self.content_cleaner.clean_docusaurus_content(raw_text)
            cleaned_text = cleaning_result["cleaned_content"]

            # Create chunks
            chunks = self.chunking_service.create_chunks(
                text=cleaned_text,
                source_file_path=file_path
            )

            # Validate chunks
            validation_results = self.chunking_service.validate_chunks(chunks)
            if validation_results["invalid_chunks"] > 0:
                self.logger.warning(
                    "File has invalid chunks",
                    file_path=file_path,
                    invalid_count=validation_results["invalid_chunks"]
                )

            # Save chunks to target directory (optional - could be implemented based on requirements)
            # For now, we'll just return the chunks

            result = {
                "file_path": file_path,
                "success": True,
                "chunks": chunks,
                "chunk_count": len(chunks),
                "extraction_metadata": extraction_result["extraction_metadata"],
                "cleaning_metadata": cleaning_result["cleaning_metadata"]
            }

            log_ingestion_event(
                event="file_processed_success",
                file_path=file_path,
                status="success",
                chunks_created=len(chunks)
            )

            return result

        except Exception as e:
            self.logger.error("Failed to process file", file_path=file_path, error=str(e))
            log_ingestion_event(
                event="file_processed_failed",
                file_path=file_path,
                status="error",
                error=str(e)
            )
            return {
                "file_path": file_path,
                "success": False,
                "error": str(e)
            }

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of an ingestion job.

        Args:
            job_id: ID of the job to check

        Returns:
            Dictionary with job status information or None if job not found
        """
        job = self.active_jobs.get(job_id)
        if job is None:
            return None

        return {
            "job_id": job.job_id,
            "status": job.status,
            "progress": {
                "total_files": job.total_files,
                "processed_files": job.processed_files,
                "failed_files": job.failed_files,
                "percentage": job.progress_percentage
            },
            "summary": {
                "start_time": job.start_time,
                "end_time": job.end_time,
                "estimated_duration": job.estimated_duration
            }
        }

    async def run_incremental_ingestion(
        self,
        source_directory: str,
        target_directory: str = None,
        max_concurrent_files: int = 5
    ) -> Dict[str, Any]:
        """
        Run incremental ingestion, processing only changed files.

        Args:
            source_directory: Directory containing markdown files to process
            target_directory: Directory to save processed chunks
            max_concurrent_files: Maximum number of files to process concurrently

        Returns:
            Dictionary with ingestion results
        """
        return await self.run_ingestion_pipeline(
            source_directory=source_directory,
            target_directory=target_directory,
            force_reprocess=False,  # Only process changed files
            max_concurrent_files=max_concurrent_files
        )

    def get_ingestion_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the ingestion service.

        Returns:
            Dictionary with ingestion statistics
        """
        return {
            "active_jobs": len(self.active_jobs),
            "active_job_ids": list(self.active_jobs.keys()),
            "service_status": "healthy" if self.health_check() else "unhealthy",
            "components": {
                "file_traversal": self.file_traversal.health_check(),
                "text_extraction": self.text_extraction.health_check(),
                "content_cleaner": self.content_cleaner.health_check(),
                "chunking_service": self.chunking_service.health_check(),
                "change_detector": self.change_detector.health_check()
            }
        }

    async def process_file_batch(
        self,
        file_paths: List[str],
        target_directory: str = None,
        max_concurrent_files: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of specific files.

        Args:
            file_paths: List of specific file paths to process
            target_directory: Directory to save processed chunks
            max_concurrent_files: Maximum number of files to process concurrently

        Returns:
            List of processing results for each file
        """
        if target_directory is None:
            target_directory = settings.PROCESSED_CHUNKS_DIR
        ensure_directory_exists(target_directory)

        semaphore = asyncio.Semaphore(max_concurrent_files)

        async def process_file_wrapper(file_path: str):
            async with semaphore:
                return await self._process_single_file(file_path, target_directory)

        # Create tasks for all files
        tasks = [process_file_wrapper(file_path) for file_path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions that occurred
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "file_path": file_paths[i],
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        return processed_results

    def validate_ingestion_config(self, source_directory: str) -> Tuple[bool, List[str]]:
        """
        Validate the ingestion configuration.

        Args:
            source_directory: Directory to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check if source directory exists
        if not os.path.isdir(source_directory):
            issues.append(f"Source directory does not exist: {source_directory}")

        # Check if target directory is writable (create if needed)
        try:
            ensure_directory_exists(settings.PROCESSED_CHUNKS_DIR)
        except Exception as e:
            issues.append(f"Cannot create/access target directory {settings.PROCESSED_CHUNKS_DIR}: {str(e)}")

        # Check if source directory has markdown files
        if not issues:  # Only check for files if directory exists
            try:
                markdown_files = self.file_traversal.get_markdown_files(source_directory)
                if not markdown_files:
                    issues.append(f"No markdown files found in {source_directory}")
            except Exception as e:
                issues.append(f"Cannot access markdown files in {source_directory}: {str(e)}")

        is_valid = len(issues) == 0
        return is_valid, issues

    def health_check(self) -> bool:
        """
        Check if the ingestion pipeline service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Check if all component services are healthy
            return all([
                self.file_traversal.health_check(),
                self.text_extraction.health_check(),
                self.content_cleaner.health_check(),
                self.chunking_service.health_check(),
                self.change_detector.health_check()
            ])
        except Exception:
            return False