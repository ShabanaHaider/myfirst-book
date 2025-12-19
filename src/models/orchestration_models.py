"""
Orchestration Request/Response Models for RAG Chatbot

This module defines data models for the orchestration layer's request and response objects.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class OrchestrationStatus(str, Enum):
    """Enumeration of possible orchestration statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ChunkMetadata(BaseModel):
    """
    Metadata for a retrieved document chunk.
    """
    source_file_path: str = Field(..., description="Path to the source file")
    chunk_index: int = Field(..., description="Index of the chunk in the original document")
    character_position: int = Field(..., description="Starting character position in the original document")
    content_hash: str = Field(..., description="Hash of the chunk content for deduplication")
    original_content_length: int = Field(..., description="Length of the original chunk content")
    score: Optional[float] = Field(None, description="Similarity score from retrieval")
    title: Optional[str] = Field(None, description="Title of the chunk/section")
    section: Optional[str] = Field(None, description="Section name where the chunk appears")


class RetrievedChunk(BaseModel):
    """
    Model for a retrieved document chunk with its metadata.
    """
    id: str = Field(..., description="Unique identifier for the chunk")
    content: str = Field(..., description="The actual content of the chunk")
    metadata: ChunkMetadata = Field(..., description="Metadata associated with the chunk")
    created_at: datetime = Field(default_factory=datetime.now, description="When the chunk was created")


class OrchestrationRequest(BaseModel):
    """
    Model for an orchestration request.
    """
    query: str = Field(..., description="The original user query")
    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list, description="List of retrieved document chunks")
    context_parameters: Dict[str, Any] = Field(default_factory=dict, description="Token limits, model settings, and formatting preferences")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the request was created")
    user_id: Optional[str] = Field(None, description="ID of the user making the request")
    session_id: Optional[str] = Field(None, description="Session ID for the request")
    timeout_seconds: Optional[float] = Field(30.0, description="Timeout for the orchestration process")
    max_chunks: Optional[int] = Field(5, description="Maximum number of chunks to include in the response")
    min_similarity_score: Optional[float] = Field(0.5, description="Minimum similarity score for retrieved chunks")
    include_source_citations: Optional[bool] = Field(True, description="Whether to include source citations in the response")
    temperature: Optional[float] = Field(None, description="Temperature setting for the LLM response")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens for the LLM response")
    model_name: Optional[str] = Field(None, description="Model name to use for the response")
    fallback_strategy: Optional[str] = Field("progressive_trimming", description="Fallback strategy to use when context exceeds token limits")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SourceAttribution(BaseModel):
    """
    Model for source attribution in responses.
    """
    chunk_id: str = Field(..., description="ID of the source chunk")
    source_file_path: str = Field(..., description="Path to the source file")
    chunk_index: int = Field(..., description="Index of the chunk in the original document")
    similarity_score: Optional[float] = Field(None, description="Similarity score of this chunk to the query")
    snippet: str = Field("", description="Brief snippet from the source for reference")


class LLMUsageMetrics(BaseModel):
    """
    Model for tracking LLM usage metrics.
    """
    prompt_tokens: int = Field(0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(0, description="Number of tokens in the completion")
    total_tokens: int = Field(0, description="Total number of tokens used")
    model_name: str = Field("", description="Name of the model used")
    processing_time_ms: float = Field(0.0, description="Time taken for LLM processing in milliseconds")


class OrchestrationResponse(BaseModel):
    """
    Model for an orchestration response.
    """
    answer: str = Field(..., description="The synthesized answer from the LLM")
    sources: List[SourceAttribution] = Field(default_factory=list, description="List of source attributions for retrieved chunks")
    confidence: Optional[float] = Field(None, description="Confidence score for the response")
    usage_metrics: Optional[LLMUsageMetrics] = Field(None, description="Usage metrics for the LLM call")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the response was generated")
    status: OrchestrationStatus = Field(OrchestrationStatus.COMPLETED, description="Status of the orchestration")
    error_message: Optional[str] = Field(None, description="Error message if status is FAILED")
    query_id: Optional[str] = Field(None, description="ID of the original query for tracking")
    processed_chunks_count: Optional[int] = Field(0, description="Number of chunks processed in the response")
    retrieval_time_ms: Optional[float] = Field(0.0, description="Time taken for retrieval in milliseconds")
    generation_time_ms: Optional[float] = Field(0.0, description="Time taken for response generation in milliseconds")
    total_time_ms: Optional[float] = Field(0.0, description="Total processing time in milliseconds")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class OrchestrationConfig(BaseModel):
    """
    Configuration model for the orchestration service.
    """
    max_context_tokens: int = Field(3000, description="Maximum tokens for context")
    max_response_tokens: int = Field(1024, description="Maximum tokens for response")
    min_chunk_score: float = Field(0.3, description="Minimum score for retrieved chunks")
    max_chunks_to_process: int = Field(10, description="Maximum number of chunks to process")
    enable_source_citations: bool = Field(True, description="Whether to enable source citations")
    fallback_to_simple_concatenation: bool = Field(False, description="Whether to fall back to simple concatenation if LLM fails")
    timeout_seconds: float = Field(30.0, description="Timeout for the entire orchestration process")
    enable_cache: bool = Field(True, description="Whether to enable caching for common queries")
    cache_ttl_seconds: int = Field(3600, description="Time-to-live for cached responses")
    enable_streaming: bool = Field(False, description="Whether to enable response streaming")
    temperature: float = Field(0.7, description="Default temperature for LLM responses")


class QueryValidationResult(BaseModel):
    """
    Model for query validation results.
    """
    is_valid: bool = Field(..., description="Whether the query is valid for processing")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    processed_query: Optional[str] = Field(None, description="Processed version of the query if it was modified")
    query_type: Optional[str] = Field(None, description="Detected type of query")


def create_default_request(query: str, retrieved_chunks: List[RetrievedChunk] = None) -> OrchestrationRequest:
    """
    Create a default orchestration request with reasonable defaults.

    Args:
        query: The user's query
        retrieved_chunks: List of retrieved chunks (optional)

    Returns:
        OrchestrationRequest: A request with default parameters
    """
    if retrieved_chunks is None:
        retrieved_chunks = []

    return OrchestrationRequest(
        query=query,
        retrieved_chunks=retrieved_chunks,
        context_parameters={
            "max_context_tokens": 2000,
            "temperature": 0.7,
            "max_tokens": 1024
        }
    )


def create_default_response(answer: str, sources: List[SourceAttribution] = None) -> OrchestrationResponse:
    """
    Create a default orchestration response with reasonable defaults.

    Args:
        answer: The answer from the LLM
        sources: List of source attributions (optional)

    Returns:
        OrchestrationResponse: A response with default parameters
    """
    if sources is None:
        sources = []

    return OrchestrationResponse(
        answer=answer,
        sources=sources,
        status=OrchestrationStatus.COMPLETED
    )


if __name__ == "__main__":
    # Example usage
    print("Orchestration Models module loaded!")

    # Create a sample request
    sample_request = OrchestrationRequest(
        query="How does the RAG system work?",
        context_parameters={
            "max_context_tokens": 2000,
            "temperature": 0.7
        }
    )
    print(f"Sample request created: {sample_request.query}")

    # Create a sample chunk
    chunk_metadata = ChunkMetadata(
        source_file_path="docs/intro.md",
        chunk_index=1,
        character_position=0,
        content_hash="abc123",
        original_content_length=100
    )
    sample_chunk = RetrievedChunk(
        id="chunk-1",
        content="The RAG system retrieves relevant documents and uses LLMs to generate responses.",
        metadata=chunk_metadata
    )

    # Create a sample response
    source_attribution = SourceAttribution(
        chunk_id="chunk-1",
        source_file_path="docs/intro.md",
        chunk_index=1,
        snippet="The RAG system retrieves relevant documents..."
    )
    sample_response = OrchestrationResponse(
        answer="The RAG system works by retrieving relevant documents from storage and using a large language model to generate human-readable responses based on that context.",
        sources=[source_attribution]
    )
    print(f"Sample response created with answer length: {len(sample_response.answer)}")