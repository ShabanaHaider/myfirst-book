"""
Response generation module for creating answers with sources.
"""
from typing import List, Dict, Any, Optional
import logging
from src.utils.text_utils import clean_text, normalize_whitespace
from src.utils.logging import StructuredLogger
from src.models.document_chunk import DocumentChunk
from src.exceptions import QueryError


class ResponseGenerator:
    """
    Module for generating responses to user queries with source attribution.
    """

    def __init__(self):
        """Initialize the response generator."""
        self.logger = StructuredLogger("response_generator")

    def generate_response(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        max_context_length: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate a response based on search results.

        Args:
            query: The original user query
            search_results: List of search results from the retrieval service
            max_context_length: Maximum length of context to include in response

        Returns:
            Dictionary with response and metadata
        """
        try:
            if not search_results:
                return {
                    "response": "I couldn't find any relevant information to answer your query.",
                    "sources": [],
                    "confidence": 0.0,
                    "query": query
                }

            # Build context from the search results
            context_parts = []
            sources = []
            total_length = 0

            for result in search_results:
                payload = result.get('payload', {})
                text_content = payload.get('text_content', '')
                source_file = payload.get('source_file_path', 'Unknown')
                chunk_index = payload.get('chunk_index', -1)
                score = result.get('score', 0.0)

                # Check if adding this context would exceed the limit
                if total_length + len(text_content) > max_context_length:
                    break

                context_parts.append(text_content)
                sources.append({
                    "source_file": source_file,
                    "chunk_index": chunk_index,
                    "similarity_score": score,
                    "text_preview": text_content[:200] + "..." if len(text_content) > 200 else text_content
                })
                total_length += len(text_content)

            # Generate a response based on the context
            response_text = self._synthesize_response(query, context_parts)

            # Calculate overall confidence based on the highest similarity score
            confidence = max([result.get('score', 0.0) for result in search_results], default=0.0)

            # Implement response time optimization by limiting response length if needed
            if len(response_text) > 2000:  # If response is too long
                sentences = response_text.split('. ')
                optimized_response = ""
                for sentence in sentences:
                    if len(optimized_response) + len(sentence) < 1500:  # Limit to 1500 chars
                        optimized_response += sentence + ". "
                    else:
                        optimized_response += "... (response truncated for performance)"
                        break
                response_text = optimized_response

            return {
                "response": response_text,
                "sources": sources,
                "confidence": confidence,
                "query": query,
                "retrieved_chunks_count": len(sources)
            }

        except Exception as e:
            self.logger.error("Failed to generate response", query=query, error=str(e))
            raise QueryError(f"Failed to generate response: {str(e)}")

    def _synthesize_response(self, query: str, context_parts: List[str]) -> str:
        """
        Synthesize a response based on the query and context.

        Args:
            query: The original user query
            context_parts: List of context parts retrieved from documents

        Returns:
            Generated response string
        """
        if not context_parts:
            return "I couldn't find any relevant information to answer your query."

        # Combine all context parts
        combined_context = " ".join(context_parts)

        # For now, create a simple response that references the context
        # In a more sophisticated implementation, you might use an LLM to generate
        # a more natural response based on the context
        response = f"Based on the documentation, here's what I found regarding '{query}':\n\n"
        response += combined_context[:1000]  # Limit response length
        if len(combined_context) > 1000:
            response += "...\n\n(Additional context was available but not included due to length.)"

        return response.strip()

    def generate_condensed_response(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        max_response_length: int = 500
    ) -> Dict[str, Any]:
        """
        Generate a condensed response with key information.

        Args:
            query: The original user query
            search_results: List of search results
            max_response_length: Maximum length of the response

        Returns:
            Dictionary with condensed response and metadata
        """
        full_response = self.generate_response(query, search_results, max_response_length * 2)

        # Condense the response if it's too long
        response_text = full_response["response"]
        if len(response_text) > max_response_length:
            # Try to find a good breaking point
            sentences = response_text.split('. ')
            condensed_parts = []
            current_length = 0

            for sentence in sentences:
                if current_length + len(sentence) + 2 <= max_response_length - 3:  # +2 for '. ' and -3 for '...'
                    condensed_parts.append(sentence)
                    current_length += len(sentence) + 2
                else:
                    break

            response_text = '. '.join(condensed_parts) + '...'
            full_response["response"] = response_text

        return full_response

    def format_sources(self, sources: List[Dict[str, Any]]) -> str:
        """
        Format sources for display in the response.

        Args:
            sources: List of source information

        Returns:
            Formatted string of sources
        """
        if not sources:
            return "No sources available."

        formatted_sources = []
        for i, source in enumerate(sources, 1):
            source_str = f"{i}. {source['source_file']} (Chunk {source['chunk_index']}, Score: {source['similarity_score']:.2f})"
            formatted_sources.append(source_str)

        return "Sources:\n" + "\n".join(formatted_sources)

    def calculate_response_confidence(self, search_results: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence score for the response based on search results.

        Args:
            search_results: List of search results

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not search_results:
            return 0.0

        # Calculate confidence based on average and maximum similarity scores
        scores = [result.get('score', 0.0) for result in search_results]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0

        # Weight the confidence based on both average and maximum scores
        confidence = (avg_score * 0.4) + (max_score * 0.6)

        # Ensure confidence is between 0 and 1
        return min(1.0, max(0.0, confidence))

    def generate_fallback_response(self, query: str) -> Dict[str, Any]:
        """
        Generate a fallback response when no relevant information is found.

        Args:
            query: The original user query

        Returns:
            Fallback response dictionary
        """
        return {
            "response": f"I couldn't find specific information about '{query}' in the documentation. Please try rephrasing your question or check if the topic is covered in the documentation.",
            "sources": [],
            "confidence": 0.0,
            "query": query,
            "retrieved_chunks_count": 0
        }

    def validate_response_quality(
        self,
        response: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Validate the quality of the generated response.

        Args:
            response: The response dictionary
            query: The original query

        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "issues": [],
            "quality_score": 0.0
        }

        response_text = response.get("response", "")
        sources = response.get("sources", [])

        # Check if response is empty
        if not response_text.strip():
            validation_result["is_valid"] = False
            validation_result["issues"].append("Response is empty")
        elif len(response_text) < 10:
            validation_result["issues"].append("Response is very short")

        # Check if sources exist
        if not sources:
            validation_result["issues"].append("No sources provided")

        # Calculate quality score based on various factors
        quality_score = 0.0

        # Length bonus
        if len(response_text) > 50:
            quality_score += 0.3
        if len(response_text) > 100:
            quality_score += 0.2

        # Source bonus
        if len(sources) > 0:
            quality_score += 0.3
        if len(sources) > 3:
            quality_score += 0.2

        # Confidence bonus
        confidence = response.get("confidence", 0.0)
        quality_score += confidence * 0.5  # Weight confidence heavily

        validation_result["quality_score"] = min(1.0, quality_score)

        return validation_result

    def enhance_response_with_context(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        original_response: str
    ) -> str:
        """
        Enhance an original response with additional context from search results.

        Args:
            query: The original user query
            search_results: List of search results
            original_response: The original response to enhance

        Returns:
            Enhanced response string
        """
        if not search_results:
            return original_response

        # Add source attribution to the response
        enhanced_response = original_response

        # Add sources if they're not already included
        if "Sources:" not in original_response and search_results:
            sources_text = self.format_sources(search_results[:3])  # Limit to top 3 sources
            enhanced_response += f"\n\n{sources_text}"

        return enhanced_response.strip()