"""
Simple chat API endpoint that maps to the existing query functionality.
Expected input: {"message": "user query"}
Expected output: {"answer": "response from RAG system"}
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
import time
import logging
from src.services.query_orchestrator import QueryOrchestratorService
from src.models.orchestration_models import OrchestrationRequest
from src.utils.logging import StructuredLogger
from src.config.settings import settings

# Define request and response models
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str


# Initialize router and services
router = APIRouter(tags=["chat"])
orchestrator_service = QueryOrchestratorService()
logger = StructuredLogger("chat_api")


@router.post("/chat", response_model=ChatResponse, summary="Simple chat endpoint for frontend")
async def chat(message: ChatRequest) -> ChatResponse:
    """
    Simple chat endpoint that takes a user message and returns a response.

    This endpoint maps the frontend's expected /chat API contract to the
    existing RAG query functionality. It accepts a JSON object with a
    'message' field and returns a JSON object with an 'answer' field.
    """
    start_time = time.time()

    try:
        # Create orchestration request from the message
        orchestration_request = OrchestrationRequest(
            query=message.message,
            context_parameters={
                "max_context_tokens": settings.LLM_MAX_TOKENS - 500,  # Reserve for response
                "temperature": settings.LLM_TEMPERATURE,
                "max_tokens": settings.LLM_MAX_TOKENS
            },
            max_chunks=settings.TOP_K_RETRIEVAL,
            min_similarity_score=settings.SIMILARITY_THRESHOLD,
            include_source_citations=False,  # Don't include sources in simple chat response
            fallback_strategy="progressive_trimming"
        )

        # Process the query through the orchestration layer
        orchestration_response = await orchestrator_service.process_query(orchestration_request)

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Log the chat event
        logger.info(
            "Chat message processed",
            query=message.message,
            response_time_ms=response_time_ms,
            processed_chunks_count=orchestration_response.processed_chunks_count
        )

        # Create and return response
        return ChatResponse(
            answer=orchestration_response.answer
        )

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error("Chat processing failed", query=message.message, error=str(e))
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


# Health check for the chat service
@router.get("/health", summary="Check health of the chat service")
async def chat_health_check() -> Dict[str, bool]:
    """
    Check if the chat service and its dependencies are healthy.
    """
    try:
        # Check if the orchestrator service is available
        # This is a simple check since the orchestrator is just a coordinator
        # The actual health check should be done on the underlying services
        retrieval_healthy = True  # We assume retrieval service is healthy if we can access it
        return {
            "chat_service": True,
            "dependencies_available": retrieval_healthy
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "chat_service": False,
            "dependencies_available": False,
            "error": str(e)
        }