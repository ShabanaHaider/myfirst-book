"""
Query Orchestration Service for RAG Chatbot

This module orchestrates the retrieval and generation process,
coordinating between the retrieval service and the LLM to produce
human-readable, synthesized responses.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from src.services.retrieval_service import RetrievalService
from src.models.orchestration_models import (
    OrchestrationRequest,
    OrchestrationResponse,
    RetrievedChunk,
    SourceAttribution,
    LLMUsageMetrics,
    OrchestrationStatus
)
from src.models.prompt_template import format_rag_prompt, get_default_rag_template
from src.services.context_manager import ContextManager
from src.utils.token_utils import token_counter
from src.config.settings import settings
from agent import gemini_agent, get_gemini_completion_async


class QueryOrchestratorService:
    """
    Service that coordinates retrieval results with response generation
    through an orchestration layer.
    """

    def __init__(self):
        """Initialize the query orchestration service."""
        self.logger = logging.getLogger(__name__)
        self.retrieval_service = RetrievalService()
        self.context_manager = ContextManager()
        self.gemini_client = gemini_agent

    async def process_query(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Process a query through the orchestration layer.

        Args:
            request: The orchestration request containing query and parameters

        Returns:
            OrchestrationResponse: The synthesized response with sources and metrics
        """
        start_time = datetime.now()
        try:
            # Log the incoming request
            self.logger.info(f"Processing orchestration request for query: {request.query[:100]}...")

            # Step 1: Retrieve relevant chunks if not provided
            retrieval_start = datetime.now()
            if not request.retrieved_chunks:
                retrieved_chunks = await self.retrieval_service.retrieve_similar_documents(
                    query=request.query,
                    top_k=request.max_chunks or settings.TOP_K_RETRIEVAL,
                    similarity_threshold=request.min_similarity_score or settings.SIMILARITY_THRESHOLD
                )

                # Convert to RetrievedChunk objects
                retrieved_chunks_objects = []
                for chunk_data in retrieved_chunks:
                    if 'payload' in chunk_data and 'source_file_path' in chunk_data['payload']:
                        chunk_obj = RetrievedChunk(
                            id=chunk_data.get('id', ''),
                            content=chunk_data['payload'].get('content', ''),
                            metadata={
                                'source_file_path': chunk_data['payload']['source_file_path'],
                                'chunk_index': chunk_data['payload'].get('chunk_index', 0),
                                'character_position': chunk_data['payload'].get('character_position', 0),
                                'content_hash': chunk_data['payload'].get('content_hash', ''),
                                'original_content_length': len(chunk_data['payload'].get('content', '')),
                                'score': chunk_data.get('score', 0.0)
                            }
                        )
                        retrieved_chunks_objects.append(chunk_obj)
            else:
                retrieved_chunks_objects = request.retrieved_chunks

            retrieval_time = (datetime.now() - retrieval_start).total_seconds() * 1000  # ms

            # Step 2: Optimize context using the context manager
            context_start = datetime.now()

            # Use the retrieved chunks (either from request or newly retrieved) for context optimization
            chunks_to_optimize = retrieved_chunks_objects if not request.retrieved_chunks else request.retrieved_chunks
            optimized_chunks = self.context_manager.select_chunks_for_context(
                chunks=chunks_to_optimize,
                query=request.query,
                max_context_tokens=request.context_parameters.get(
                    'max_context_tokens',
                    settings.LLM_MAX_TOKENS - 500  # Reserve for prompt and response
                ),
                max_chunks=request.max_chunks,
                min_similarity_score=request.min_similarity_score
            )

            # Check if the optimized context fits within token limits, apply fallback if needed
            max_context_tokens = request.context_parameters.get(
                'max_context_tokens',
                settings.LLM_MAX_TOKENS - 500  # Reserve for prompt and response
            )

            # Check if the context exceeds token limits and apply fallback strategies if needed
            if not self.context_manager.validate_context_fits_model(optimized_chunks, request.query, max_context_tokens):
                self.logger.warning(f"Context exceeds token limits ({len(optimized_chunks)} chunks, {max_context_tokens} max tokens), applying fallback strategies")

                # Apply fallback strategies to reduce context size
                optimized_chunks = self.context_manager.apply_fallback_strategies(
                    optimized_chunks,
                    request.query,
                    max_context_tokens,
                    strategy=request.fallback_strategy
                )

                # Log the results of fallback application
                if optimized_chunks:
                    summary = self.context_manager.get_context_summary(optimized_chunks, request.query)
                    self.logger.info(f"Fallback strategies applied: reduced to {summary['num_chunks']} chunks, {summary['total_tokens']} total tokens")
                else:
                    self.logger.warning("Fallback strategies could not reduce context to fit within token limits")

            context_time = (datetime.now() - context_start).total_seconds() * 1000  # ms

            # Step 3: Format the context for the LLM
            context_dicts = []
            for chunk in optimized_chunks:
                context_dicts.append({
                    'content': chunk.content,
                    'source_file_path': chunk.metadata.source_file_path,
                    'chunk_index': chunk.metadata.chunk_index,
                    'score': chunk.metadata.score
                })

            # Step 4: Construct prompt with retrieved chunks and user query
            prompt_text = self._construct_prompt_with_context(
                query=request.query,
                context_chunks=optimized_chunks,
                request=request
            )

            # Step 5: Call the LLM to generate the response
            generation_start = datetime.now()
            prompt_str = prompt_text

            # Determine model and parameters
            model_name = request.model_name or settings.LLM_MODEL_NAME
            temperature = request.temperature or settings.LLM_TEMPERATURE
            max_tokens = request.max_tokens or settings.LLM_MAX_TOKENS

            # Update settings temporarily if needed
            original_temp = settings.LLM_TEMPERATURE
            original_max_tokens = settings.LLM_MAX_TOKENS
            settings.LLM_TEMPERATURE = temperature
            settings.LLM_MAX_TOKENS = max_tokens

            try:
                llm_response = await get_gemini_completion_async(
                    self.gemini_client,
                    prompt_str,
                    model=model_name
                )
            finally:
                # Restore original settings
                settings.LLM_TEMPERATURE = original_temp
                settings.LLM_MAX_TOKENS = original_max_tokens

            generation_time = (datetime.now() - generation_start).total_seconds() * 1000  # ms

            # Step 6: Calculate usage metrics
            prompt_tokens = token_counter.count_tokens(prompt_str)
            completion_tokens = token_counter.count_tokens(llm_response)
            usage_metrics = LLMUsageMetrics(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                model_name=model_name,
                processing_time_ms=generation_time
            )

            # Step 7: Create source attributions
            sources = []
            for chunk in optimized_chunks:
                if request.include_source_citations:
                    source = SourceAttribution(
                        chunk_id=chunk.id,
                        source_file_path=chunk.metadata.source_file_path,
                        chunk_index=chunk.metadata.chunk_index,
                        similarity_score=chunk.metadata.score,
                        snippet=chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
                    )
                    sources.append(source)

            # Step 8: Create the final response
            total_time = (datetime.now() - start_time).total_seconds() * 1000  # ms
            response = OrchestrationResponse(
                answer=llm_response,
                sources=sources,
                usage_metrics=usage_metrics,
                status=OrchestrationStatus.COMPLETED,
                processed_chunks_count=len(optimized_chunks),
                retrieval_time_ms=retrieval_time,
                generation_time_ms=generation_time,
                total_time_ms=total_time
            )

            self.logger.info(f"Successfully processed orchestration request in {total_time:.2f}ms")
            return response

        except Exception as e:
            self.logger.error(f"Error processing orchestration request: {str(e)}", exc_info=True)
            total_time = (datetime.now() - start_time).total_seconds() * 1000  # ms

            return OrchestrationResponse(
                answer="I'm sorry, but I encountered an error while processing your request. Please try again.",
                sources=[],
                status=OrchestrationStatus.FAILED,
                error_message=str(e),
                total_time_ms=total_time
            )

    async def process_query_with_fallback(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Process a query with fallback to simple concatenation if LLM fails.

        Args:
            request: The orchestration request containing query and parameters

        Returns:
            OrchestrationResponse: The response, potentially using fallback method
        """
        try:
            # First, try the normal orchestration process
            response = await self.process_query(request)

            # If the response was successful, return it
            if response.status != OrchestrationStatus.FAILED:
                return response

            # If it failed and fallback is enabled, try simple concatenation
            if settings.fallback_to_simple_concatenation:
                return await self._fallback_response(request)
            else:
                return response  # Return the failed response

        except Exception as e:
            self.logger.error(f"Error in orchestration with fallback: {str(e)}", exc_info=True)

            return OrchestrationResponse(
                answer="I'm sorry, but I encountered an error while processing your request. Please try again.",
                sources=[],
                status=OrchestrationStatus.FAILED,
                error_message=str(e)
            )

    async def _fallback_response(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Generate a fallback response by concatenating retrieved content.

        Args:
            request: The orchestration request

        Returns:
            OrchestrationResponse: Fallback response
        """
        self.logger.warning("Using fallback response generation due to LLM failure")

        try:
            # Get retrieved chunks
            if not request.retrieved_chunks:
                retrieved_chunks = await self.retrieval_service.retrieve_similar_documents(
                    query=request.query,
                    top_k=request.max_chunks or settings.TOP_K_RETRIEVAL,
                    similarity_threshold=request.min_similarity_score or settings.SIMILARITY_THRESHOLD
                )

                # Convert to RetrievedChunk objects (similar to main process)
                retrieved_chunks_objects = []
                for chunk_data in retrieved_chunks:
                    if 'payload' in chunk_data and 'source_file_path' in chunk_data['payload']:
                        chunk_obj = RetrievedChunk(
                            id=chunk_data.get('id', ''),
                            content=chunk_data['payload'].get('content', ''),
                            metadata={
                                'source_file_path': chunk_data['payload']['source_file_path'],
                                'chunk_index': chunk_data['payload'].get('chunk_index', 0),
                                'character_position': chunk_data['payload'].get('character_position', 0),
                                'content_hash': chunk_data['payload'].get('content_hash', ''),
                                'original_content_length': len(chunk_data['payload'].get('content', '')),
                                'score': chunk_data.get('score', 0.0)
                            }
                        )
                        retrieved_chunks_objects.append(chunk_obj)
            else:
                retrieved_chunks_objects = request.retrieved_chunks

            # Create a simple concatenated response
            concatenated_content = "\n\n".join([chunk.content for chunk in retrieved_chunks_objects[:3]])  # Limit to top 3
            fallback_answer = f"Based on the documentation:\n\n{concatenated_content}\n\nFor more details, please refer to the original documentation."

            # Create source attributions
            sources = []
            for chunk in retrieved_chunks_objects:
                if request.include_source_citations:
                    source = SourceAttribution(
                        chunk_id=chunk.id,
                        source_file_path=chunk.metadata.source_file_path,
                        chunk_index=chunk.metadata.chunk_index,
                        similarity_score=chunk.metadata.score,
                        snippet=chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
                    )
                    sources.append(source)

            return OrchestrationResponse(
                answer=fallback_answer,
                sources=sources,
                status=OrchestrationStatus.COMPLETED,
                processed_chunks_count=len(retrieved_chunks_objects)
            )

        except Exception as e:
            self.logger.error(f"Error in fallback response generation: {str(e)}", exc_info=True)
            return OrchestrationResponse(
                answer="I'm sorry, but I couldn't retrieve the information you requested.",
                sources=[],
                status=OrchestrationStatus.FAILED,
                error_message=str(e)
            )

    def get_context_summary(self, request: OrchestrationRequest) -> Dict[str, Any]:
        """
        Get a summary of the context that would be used for the request.

        Args:
            request: The orchestration request

        Returns:
            Dictionary with context summary information
        """
        # Optimize context for the request
        optimized_chunks = self.context_manager.optimize_context_for_query(request)

        # Get summary from context manager
        return self.context_manager.get_context_summary(optimized_chunks, request.query)

    async def validate_query(self, request: OrchestrationRequest) -> Tuple[bool, List[str]]:
        """
        Validate an orchestration request before processing.

        Args:
            request: The orchestration request to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check if query is provided and not empty
        if not request.query or not request.query.strip():
            errors.append("Query cannot be empty")

        # Check if query is too long
        if len(request.query) > settings.MAX_QUERY_LENGTH:
            errors.append(f"Query exceeds maximum length of {settings.MAX_QUERY_LENGTH} characters")

        # Check if API keys are available
        if not settings.GEMINI_API_KEY and not settings.COHERE_API_KEY:
            errors.append("Either GEMINI_API_KEY or COHERE_API_KEY must be configured")

        return len(errors) == 0, errors

    def _construct_prompt_with_context(
        self,
        query: str,
        context_chunks: List[RetrievedChunk],
        request: OrchestrationRequest
    ) -> str:
        """
        Construct a prompt by combining user query with retrieved context chunks,
        enforcing token limits to ensure it fits within model constraints.

        Args:
            query: The user's query
            context_chunks: List of relevant context chunks
            request: The orchestration request with parameters

        Returns:
            str: The constructed prompt ready for LLM consumption
        """
        # Determine the maximum tokens allowed for context
        max_context_tokens = request.context_parameters.get(
            'max_context_tokens',
            settings.LLM_MAX_TOKENS - 500  # Reserve tokens for system message, query, and response
        )

        # Create the system message
        system_message = (
            "You are a helpful AI assistant for the myfirst_book documentation. "
            "Use the provided context to answer questions accurately. "
            "If the context doesn't contain the information needed to answer, say so. "
            "Be concise but comprehensive in your responses and cite sources when possible."
        )

        # Format the user query
        query_section = f"## User Query:\n{query}\n\n"

        # Create the instruction
        instruction = (
            "## Instructions:\n"
            "Based on the retrieved context above, please provide a helpful and accurate answer to the user's query. "
            "If the context contains relevant information, use it to form your response. "
            "If the context doesn't contain sufficient information, acknowledge this limitation. "
            "Cite the sources you used from the context when possible."
        )

        # Calculate tokens used by system message, query, and instruction
        system_tokens = token_counter.count_tokens(system_message)
        query_tokens = token_counter.count_tokens(query_section)
        instruction_tokens = token_counter.count_tokens(instruction)
        overhead_tokens = system_tokens + query_tokens + instruction_tokens + 100  # Additional overhead

        # Calculate remaining tokens for context
        remaining_context_tokens = max_context_tokens - overhead_tokens

        if remaining_context_tokens <= 0:
            # If there's no room for context, return a prompt with just the query
            self.logger.warning("No tokens available for context, proceeding with query only")
            return f"{system_message}\n\n{query_section}{instruction}"

        # Format the context chunks, ensuring they fit within token limits
        context_section = "## Retrieved Context:\n\n"
        accumulated_tokens = 0

        for i, chunk in enumerate(context_chunks, 1):
            # Format this chunk
            chunk_header = f"### Source {i} (from {chunk.metadata.source_file_path}):\n"
            chunk_content = chunk.content
            chunk_footer = "\n\n"

            # Calculate tokens for this chunk
            header_tokens = token_counter.count_tokens(chunk_header)
            content_tokens = token_counter.count_tokens(chunk_content)
            footer_tokens = token_counter.count_tokens(chunk_footer)

            total_chunk_tokens = header_tokens + content_tokens + footer_tokens

            # Check if adding this chunk would exceed limits
            if accumulated_tokens + total_chunk_tokens > remaining_context_tokens:
                # Try to truncate the content to fit
                available_content_tokens = remaining_context_tokens - accumulated_tokens - header_tokens - footer_tokens

                if available_content_tokens > 0:
                    truncated_content = token_counter.truncate_text_to_tokens(chunk_content, available_content_tokens)
                    if truncated_content.strip():  # Only add if there's meaningful content
                        context_section += f"{chunk_header}{truncated_content}{chunk_footer}"
                        self.logger.info(f"Truncated chunk {i} to fit token limits")

                # No more space for additional chunks
                self.logger.info(f"Context truncated after {i} chunks due to token limits")
                break
            else:
                # Add the full chunk
                context_section += f"{chunk_header}{chunk_content}{chunk_footer}"
                accumulated_tokens += total_chunk_tokens

        # Combine all parts
        full_prompt = f"{system_message}\n\n{context_section}{query_section}{instruction}"

        # Final validation to ensure the prompt fits within limits
        total_prompt_tokens = token_counter.count_tokens(full_prompt)
        if total_prompt_tokens > max_context_tokens:
            self.logger.warning(
                f"Prompt exceeds token limit ({total_prompt_tokens} > {max_context_tokens}), "
                f"actual context may be further reduced by the LLM provider"
            )

        return full_prompt


def create_default_orchestrator() -> QueryOrchestratorService:
    """
    Create a default query orchestrator service instance.

    Returns:
        QueryOrchestratorService: A new orchestrator service instance
    """
    return QueryOrchestratorService()


if __name__ == "__main__":
    # Example usage (this would typically run in an async context)
    import asyncio

    async def example():
        print("Query Orchestrator Service module loaded!")

        # Create orchestrator
        orchestrator = QueryOrchestratorService()

        # Create a sample request
        request = OrchestrationRequest(
            query="What is the RAG system architecture?",
            max_chunks=3,
            min_similarity_score=0.5
        )

        print(f"Sample request created: {request.query}")
        print(f"Max chunks: {request.max_chunks}")
        print(f"Min similarity score: {request.min_similarity_score}")

        # Note: This would actually call the LLM if run with valid API keys
        # For now, we'll just show what would happen
        print("Orchestrator ready to process queries!")

    # asyncio.run(example())