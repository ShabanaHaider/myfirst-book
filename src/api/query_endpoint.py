"""
API endpoint for querying with /query POST route.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import time
import logging
from pydantic import BaseModel, Field
from src.services.retrieval_service import RetrievalService
from src.query.query_processor import QueryProcessor
from src.query.response_generator import ResponseGenerator
from src.utils.logging import StructuredLogger, log_api_call, log_query_event
from src.config.settings import settings
from src.exceptions import QueryError, ValidationError


# Define request and response models
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=settings.MAX_QUERY_LENGTH,
                      description="The question to ask about the documentation")
    top_k: int = Field(default=settings.TOP_K_RETRIEVAL, ge=1, le=20,
                      description="Number of results to retrieve (default: 5, max: 20)")
    similarity_threshold: float = Field(default=settings.SIMILARITY_THRESHOLD, ge=0.0, le=1.0,
                                       description="Minimum similarity score threshold (default: 0.7)")
    include_sources: bool = Field(default=True, description="Whether to include sources in the response")


class QueryResponse(BaseModel):
    query_id: str
    response: str
    sources: list
    confidence: float
    response_time_ms: float
    retrieved_chunks_count: int


class QueryValidationResponse(BaseModel):
    is_valid: bool
    issues: list
    suggestions: list


# Initialize router and services
router = APIRouter(prefix="/api/v1", tags=["query"])
retrieval_service = RetrievalService()
query_processor = QueryProcessor()
response_generator = ResponseGenerator()
logger = StructuredLogger("query_api")


@router.post("/query", response_model=QueryResponse, summary="Submit query and receive RAG response")
async def query_documentation(request: QueryRequest) -> QueryResponse:
    """
    Submit a query about the documentation and receive a response with sources.

    This endpoint processes the user's question, searches for relevant information
    in the documentation using semantic search, and generates a response with
    proper source attribution.
    """
    start_time = time.time()
    query_id = __import__('uuid').uuid4().hex[:8]  # Simple query ID for tracking

    try:
        # Process the query
        processed_query = await query_processor.process_query(request.query)

        # Retrieve similar documents
        search_results = await retrieval_service.retrieve_similar_documents(
            query=processed_query["processed_query"],
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )

        # Generate response
        response_data = response_generator.generate_response(
            query=request.query,
            search_results=search_results
        )

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Log the query event
        log_query_event(
            query=request.query,
            result_count=len(search_results),
            response_time_ms=response_time_ms
        )

        # Log API call
        log_api_call(
            operation="query_documentation",
            status="success",
            duration_ms=response_time_ms,
            query_id=query_id
        )

        # Create and return response
        return QueryResponse(
            query_id=query_id,
            response=response_data["response"],
            sources=response_data["sources"] if request.include_sources else [],
            confidence=response_data["confidence"],
            response_time_ms=response_time_ms,
            retrieved_chunks_count=response_data["retrieved_chunks_count"]
        )

    except ValidationError as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error("Query validation failed", query=request.query, error=str(e))
        log_api_call(
            operation="query_documentation",
            status="validation_error",
            duration_ms=response_time_ms,
            query_id=query_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))

    except QueryError as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error("Query processing failed", query=request.query, error=str(e))
        log_api_call(
            operation="query_documentation",
            status="query_error",
            duration_ms=response_time_ms,
            query_id=query_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error("Unexpected error in query endpoint", query=request.query, error=str(e))
        log_api_call(
            operation="query_documentation",
            status="error",
            duration_ms=response_time_ms,
            query_id=query_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/query/validate", response_model=QueryValidationResponse,
             summary="Validate a query before processing")
async def validate_query(request: QueryRequest) -> QueryValidationResponse:
    """
    Validate a query to check if it's suitable for processing.

    This endpoint checks the quality of the query and provides suggestions
    for improvement if needed.
    """
    try:
        validation_result = await query_processor.validate_query_quality(request.query)
        return QueryValidationResponse(
            is_valid=validation_result["is_valid"],
            issues=validation_result["issues"],
            suggestions=validation_result["suggestions"]
        )
    except Exception as e:
        logger.error("Query validation failed", query=request.query, error=str(e))
        raise HTTPException(status_code=500, detail=f"Query validation failed: {str(e)}")


@router.post("/query/expand", summary="Expand a query with related terms")
async def expand_query(query: str) -> Dict[str, Any]:
    """
    Expand a query with related terms to improve search results.
    """
    try:
        expanded_terms = await query_processor.expand_query(query)
        return {
            "original_query": query,
            "expanded_terms": expanded_terms
        }
    except Exception as e:
        logger.error("Query expansion failed", query=query, error=str(e))
        raise HTTPException(status_code=500, detail=f"Query expansion failed: {str(e)}")


@router.get("/query/stats", summary="Get query statistics")
async def get_query_stats() -> Dict[str, Any]:
    """
    Get statistics about the query service and available documentation.
    """
    try:
        collection_stats = retrieval_service.get_collection_stats()
        return {
            "collection_stats": collection_stats,
            "model_info": query_processor.cohere_client.get_model_info(),
            "settings": {
                "top_k_retrieval": settings.TOP_K_RETRIEVAL,
                "similarity_threshold": settings.SIMILARITY_THRESHOLD,
                "max_query_length": settings.MAX_QUERY_LENGTH
            }
        }
    except Exception as e:
        logger.error("Failed to get query stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get query stats: {str(e)}")


@router.post("/query/debug", include_in_schema=False)
async def debug_query(request: QueryRequest) -> Dict[str, Any]:
    """
    Debug endpoint that returns detailed information about query processing.
    This includes the processed query, embeddings, and raw search results.
    """
    try:
        # Process the query to get embedding
        processed_query = await query_processor.process_query(request.query)

        # Get search results
        search_results = await retrieval_service.retrieve_similar_documents(
            query=processed_query["processed_query"],
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )

        return {
            "original_query": request.query,
            "processed_query": processed_query["processed_query"],
            "query_embedding_length": len(processed_query["embedding"]),
            "search_results_count": len(search_results),
            "search_results": search_results[:2],  # Only return first 2 results for brevity
            "first_result_payload_keys": list(search_results[0]["payload"].keys()) if search_results else []
        }
    except Exception as e:
        logger.error("Debug query failed", query=request.query, error=str(e))
        raise HTTPException(status_code=500, detail=f"Debug query failed: {str(e)}")


# Health check for the query service
@router.get("/health", summary="Check health of the query service")
async def query_health_check() -> Dict[str, bool]:
    """
    Check if the query service and its dependencies are healthy.
    """
    try:
        retrieval_healthy = retrieval_service.health_check()
        query_processor_healthy = query_processor.health_check()

        is_healthy = retrieval_healthy and query_processor_healthy

        return {
            "query_service": is_healthy,
            "retrieval_service": retrieval_healthy,
            "query_processor": query_processor_healthy
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "query_service": False,
            "retrieval_service": False,
            "query_processor": False,
            "error": str(e)
        }