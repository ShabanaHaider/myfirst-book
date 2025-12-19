"""
Run Query - Single Entry Point for Orchestration Layer

This module provides a single entry point for the orchestration layer
that coordinates retrieval and generation to produce human-readable answers.
"""
import asyncio
import argparse
import logging
from typing import List, Optional
from src.services.query_orchestrator import QueryOrchestratorService
from src.models.orchestration_models import OrchestrationRequest, RetrievedChunk, ChunkMetadata
from src.config.settings import settings


class QueryRunner:
    """
    Class to run queries through the orchestration layer.
    """

    def __init__(self):
        """Initialize the query runner with required services."""
        self.orchestrator = QueryOrchestratorService()
        self.logger = logging.getLogger(__name__)

    async def run_query(
        self,
        query: str,
        max_chunks: int = 5,
        min_similarity_score: float = 0.5,
        include_source_citations: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_name: Optional[str] = None,
        retrieved_chunks: Optional[List[RetrievedChunk]] = None
    ):
        """
        Run a query through the orchestration layer.

        Args:
            query: The user's query
            max_chunks: Maximum number of chunks to retrieve
            min_similarity_score: Minimum similarity score for retrieved chunks
            include_source_citations: Whether to include source citations
            temperature: Temperature for LLM response (optional)
            max_tokens: Maximum tokens for LLM response (optional)
            model_name: Model name to use (optional)
            retrieved_chunks: Pre-retrieved chunks (optional)

        Returns:
            The orchestration response with the answer and sources
        """
        # Create orchestration request
        request = OrchestrationRequest(
            query=query,
            retrieved_chunks=retrieved_chunks or [],
            context_parameters={
                "max_context_tokens": settings.LLM_MAX_TOKENS - 500,  # Reserve for response
                "temperature": temperature or settings.LLM_TEMPERATURE,
                "max_tokens": max_tokens or settings.LLM_MAX_TOKENS
            },
            max_chunks=max_chunks,
            min_similarity_score=min_similarity_score,
            include_source_citations=include_source_citations,
            temperature=temperature,
            max_tokens=max_tokens,
            model_name=model_name
        )

        # Process the query through the orchestration layer
        response = await self.orchestrator.process_query(request)

        return response

    async def run_query_with_validation(
        self,
        query: str,
        max_chunks: int = 5,
        min_similarity_score: float = 0.5
    ):
        """
        Run a query with validation before processing.

        Args:
            query: The user's query
            max_chunks: Maximum number of chunks to retrieve
            min_similarity_score: Minimum similarity score for retrieved chunks

        Returns:
            The orchestration response or error information
        """
        # Create a request for validation
        request = OrchestrationRequest(
            query=query,
            max_chunks=max_chunks,
            min_similarity_score=min_similarity_score
        )

        # Validate the request
        is_valid, errors = await self.orchestrator.validate_query(request)
        if not is_valid:
            return {
                "error": "Validation failed",
                "errors": errors,
                "answer": "Unable to process query due to validation errors."
            }

        # Run the query if validation passes
        return await self.run_query(query, max_chunks, min_similarity_score)

    async def run_batch_queries(self, queries: List[str], **kwargs):
        """
        Run multiple queries through the orchestration layer.

        Args:
            queries: List of queries to process
            **kwargs: Additional parameters for all queries

        Returns:
            List of responses for each query
        """
        results = []
        for i, query in enumerate(queries):
            self.logger.info(f"Processing query {i+1}/{len(queries)}: {query[:50]}...")
            try:
                result = await self.run_query(query, **kwargs)
                results.append({
                    "query": query,
                    "result": result,
                    "status": "success"
                })
            except Exception as e:
                self.logger.error(f"Error processing query {i+1}: {str(e)}")
                results.append({
                    "query": query,
                    "result": None,
                    "status": "error",
                    "error": str(e)
                })

        return results


def setup_logging(level: str = "INFO"):
    """Set up logging for the query runner."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def main():
    """Main function to run queries from command line."""
    parser = argparse.ArgumentParser(description="Run queries through the orchestration layer")
    parser.add_argument("query", nargs='?', help="The query to process")
    parser.add_argument("--max-chunks", type=int, default=5, help="Maximum number of chunks to retrieve")
    parser.add_argument("--min-similarity", type=float, default=0.5, help="Minimum similarity score")
    parser.add_argument("--temperature", type=float, help="Temperature for LLM response")
    parser.add_argument("--max-tokens", type=int, help="Maximum tokens for LLM response")
    parser.add_argument("--model", help="Model name to use")
    parser.add_argument("--no-citations", action="store_true", help="Don't include source citations")
    parser.add_argument("--batch-file", help="File with multiple queries (one per line)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set up logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)

    # Create query runner
    runner = QueryRunner()

    if args.batch_file:
        # Read queries from file
        with open(args.batch_file, 'r', encoding='utf-8') as f:
            queries = [line.strip() for line in f if line.strip()]

        print(f"Processing {len(queries)} queries from {args.batch_file}")
        results = await runner.run_batch_queries(
            queries,
            max_chunks=args.max_chunks,
            min_similarity_score=args.min_similarity,
            include_source_citations=not args.no_citations,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            model_name=args.model
        )

        for i, result in enumerate(results):
            print(f"\n--- Query {i+1} ---")
            print(f"Query: {result['query']}")
            if result['status'] == 'success':
                print(f"Answer: {result['result'].answer}")
                if result['result'].sources and not args.no_citations:
                    print("Sources:")
                    for source in result['result'].sources:
                        print(f"  - {source.source_file_path} (Chunk {source.chunk_index})")
            else:
                print(f"Error: {result['error']}")
    else:
        if not args.query:
            print("Please provide a query or use --batch-file")
            parser.print_help()
            return

        print(f"Processing query: {args.query}")
        print(f"Max chunks: {args.max_chunks}")
        print(f"Min similarity: {args.min_similarity}")

        try:
            result = await runner.run_query(
                query=args.query,
                max_chunks=args.max_chunks,
                min_similarity_score=args.min_similarity,
                include_source_citations=not args.no_citations,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                model_name=args.model
            )

            print(f"\nAnswer: {result.answer}")
            print(f"\nProcessing time: {result.total_time_ms:.2f}ms")

            if result.sources and not args.no_citations:
                print(f"\nSources ({len(result.sources)}):")
                for i, source in enumerate(result.sources, 1):
                    snippet = source.snippet[:100] + "..." if len(source.snippet) > 100 else source.snippet
                    print(f"  {i}. {source.source_file_path} (Score: {source.similarity_score:.2f})")
                    print(f"     Snippet: {snippet}")

            if result.usage_metrics:
                print(f"\nUsage Metrics:")
                print(f"  Prompt tokens: {result.usage_metrics.prompt_tokens}")
                print(f"  Completion tokens: {result.usage_metrics.completion_tokens}")
                print(f"  Total tokens: {result.usage_metrics.total_tokens}")
                print(f"  Model: {result.usage_metrics.model_name}")

        except Exception as e:
            print(f"Error processing query: {str(e)}")
            import traceback
            traceback.print_exc()


def run_query_direct(query: str, **kwargs):
    """
    Convenience function to run a single query synchronously.

    Args:
        query: The query to process
        **kwargs: Additional parameters

    Returns:
        The orchestration response
    """
    async def _run():
        runner = QueryRunner()
        return await runner.run_query(query, **kwargs)

    return asyncio.run(_run())


def run_query_batch(queries: List[str], **kwargs):
    """
    Convenience function to run multiple queries synchronously.

    Args:
        queries: List of queries to process
        **kwargs: Additional parameters

    Returns:
        List of orchestration responses
    """
    async def _run():
        runner = QueryRunner()
        return await runner.run_batch_queries(queries, **kwargs)

    return asyncio.run(_run())


if __name__ == "__main__":
    asyncio.run(main())