"""
Context Manager for Dynamic Chunk Selection

This module provides utilities for managing context size and dynamically selecting
the most relevant chunks to fit within token limits.
"""
from typing import List, Dict, Any, Optional, Tuple
from src.models.orchestration_models import RetrievedChunk, OrchestrationRequest
from src.utils.token_utils import token_counter, get_remaining_tokens, fit_chunks_to_context
from src.config.settings import settings
import logging


class ContextManager:
    """
    Manages context size and dynamically selects the most relevant chunks
    to fit within token limits while preserving essential information.
    """

    def __init__(self):
        """Initialize the context manager."""
        self.logger = logging.getLogger(__name__)

    def select_chunks_for_context(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        max_context_tokens: Optional[int] = None,
        max_chunks: Optional[int] = None,
        min_similarity_score: Optional[float] = None
    ) -> List[RetrievedChunk]:
        """
        Select the most relevant chunks to fit within context token limits
        using intelligent trimming and selection algorithms.

        Args:
            chunks: List of retrieved chunks to select from
            query: The user query (used for relevance considerations)
            max_context_tokens: Maximum tokens allowed for context (defaults to settings)
            max_chunks: Maximum number of chunks to include
            min_similarity_score: Minimum similarity score for inclusion

        Returns:
            List of selected chunks that fit within token limits
        """
        if max_context_tokens is None:
            max_context_tokens = settings.LLM_MAX_TOKENS - 500  # Reserve for prompt and response

        if max_chunks is None:
            max_chunks = 10

        if min_similarity_score is None:
            min_similarity_score = 0.3

        # Filter chunks by minimum similarity score
        filtered_chunks = [
            chunk for chunk in chunks
            if (chunk.metadata.score is None or chunk.metadata.score >= min_similarity_score)
        ]

        # Apply intelligent selection based on multiple factors
        ranked_chunks = self._rank_chunks_intelligently(filtered_chunks, query)

        # Limit the number of chunks considered
        limited_chunks = ranked_chunks[:max_chunks]

        # Convert to the format expected by fit_chunks_to_context
        chunk_dicts = []
        for chunk in limited_chunks:
            chunk_dict = {
                'id': chunk.id,
                'content': chunk.content,
                'score': chunk.metadata.score,
                'source_file_path': chunk.metadata.source_file_path,
                'chunk_index': chunk.metadata.chunk_index
            }
            chunk_dicts.append(chunk_dict)

        # Create a realistic context template for token calculation
        context_template = (
            "## Retrieved Context:\n\n{context}\n\n"
            "## User Query:\n{query}\n\n"
            "## Instructions:\n"
            "Based on the retrieved context above, please provide a helpful and accurate answer to the user's query."
        )

        # Select and trim chunks to fit within token limits using the enhanced algorithm
        selected_chunk_dicts = self._intelligent_fit_chunks_to_context(
            chunks=chunk_dicts,
            context_template=context_template,
            query=query,
            max_context_tokens=max_context_tokens
        )

        # Convert back to RetrievedChunk objects
        selected_chunks = []
        for chunk_dict in selected_chunk_dicts:
            # Find the original chunk object
            original_chunk = next(
                (c for c in limited_chunks if c.id == chunk_dict['id']),
                None
            )
            if original_chunk:
                # If content was trimmed during fitting, use the trimmed version
                if chunk_dict.get('content') != original_chunk.content:
                    modified_chunk = original_chunk.copy()
                    modified_chunk.content = chunk_dict['content']
                    selected_chunks.append(modified_chunk)
                else:
                    selected_chunks.append(original_chunk)

        self.logger.info(
            f"Selected {len(selected_chunks)} chunks out of {len(chunks)} total chunks "
            f"for context with max {max_context_tokens} tokens"
        )

        return selected_chunks

    def _rank_chunks_intelligently(self, chunks: List[RetrievedChunk], query: str) -> List[RetrievedChunk]:
        """
        Rank chunks using multiple relevance factors beyond just similarity score.

        Args:
            chunks: List of chunks to rank
            query: The user query for relevance assessment

        Returns:
            List of chunks ranked by overall relevance
        """
        def calculate_relevance_score(chunk: RetrievedChunk) -> float:
            score = 0.0

            # Base similarity score (if available)
            base_score = chunk.metadata.score or 0.0
            score += base_score * 0.5  # Weight for semantic similarity

            # Content length factor (prefer medium-length chunks over very short or very long)
            content_length = len(chunk.content)
            if 100 <= content_length <= 1000:  # Optimal length range
                length_score = 0.3
            elif 50 <= content_length <= 2000:  # Acceptable range
                length_score = 0.1
            else:
                length_score = -0.1  # Penalize very short or very long chunks
            score += length_score

            # Position factor (earlier chunks in document might be more relevant)
            # But this is balanced with similarity score
            position_factor = 1.0 / (chunk.metadata.chunk_index + 1)
            score += position_factor * 0.1

            # Content quality factor (simple heuristic based on content richness)
            content_lower = chunk.content.lower()
            # Count key terms that indicate informative content
            key_terms = ['section', 'chapter', 'introduction', 'summary', 'overview', 'definition', 'example']
            term_count = sum(1 for term in key_terms if term in content_lower)
            quality_score = min(term_count * 0.05, 0.2)  # Cap at 0.2
            score += quality_score

            return score

        # Sort by calculated relevance score (highest first)
        ranked_chunks = sorted(chunks, key=calculate_relevance_score, reverse=True)

        return ranked_chunks

    def _intelligent_fit_chunks_to_context(
        self,
        chunks: List[Dict[str, Any]],
        context_template: str,
        query: str,
        max_context_tokens: int
    ) -> List[Dict[str, Any]]:
        """
        Intelligently fit chunks to context with advanced trimming and selection algorithms.

        Args:
            chunks: List of chunk dictionaries with content
            context_template: Template for calculating context size
            query: User query for context calculation
            max_context_tokens: Maximum tokens allowed

        Returns:
            List of chunks that fit within token limits, potentially with trimmed content
        """
        if not chunks:
            return []

        # Calculate overhead tokens (template + query)
        base_content = context_template.format(context="", query=query)
        overhead_tokens = token_counter.count_tokens(base_content)

        # Calculate available tokens for actual content
        available_tokens = max_context_tokens - overhead_tokens
        if available_tokens <= 0:
            return []  # Not enough space for any content

        selected_chunks = []
        used_tokens = 0

        for chunk in chunks:
            chunk_content = chunk.get('content', '')
            chunk_tokens = token_counter.count_tokens(chunk_content)

            if used_tokens + chunk_tokens <= available_tokens:
                # Chunk fits completely
                selected_chunks.append(chunk)
                used_tokens += chunk_tokens
            else:
                # Try to intelligently trim this chunk to fit
                remaining_tokens = available_tokens - used_tokens
                if remaining_tokens > 50:  # Only worth trimming if we have significant space
                    # Try to preserve the most important parts of the chunk
                    trimmed_content = self._intelligently_trim_chunk(
                        chunk_content,
                        remaining_tokens
                    )
                    if trimmed_content.strip():
                        trimmed_chunk = chunk.copy()
                        trimmed_chunk['content'] = trimmed_content
                        selected_chunks.append(trimmed_chunk)
                        used_tokens += token_counter.count_tokens(trimmed_content)
                    break  # No more space after adding this trimmed chunk
                else:
                    # Not worth adding a heavily trimmed chunk, so stop here
                    break

        return selected_chunks

    def _intelligently_trim_chunk(self, content: str, max_tokens: int) -> str:
        """
        Trim chunk content intelligently to preserve the most important information.

        Args:
            content: The content to trim
            max_tokens: Maximum tokens allowed

        Returns:
            Trimmed content that fits within token limits
        """
        if token_counter.count_tokens(content) <= max_tokens:
            return content

        # For intelligent trimming, we'll try to preserve:
        # 1. Beginning of content (introductions are often important)
        # 2. End of content (conclusions/summaries)
        # 3. Key sentences with important terms

        # First, try a simple truncation
        simple_truncation = token_counter.truncate_text_to_tokens(content, max_tokens)
        if token_counter.count_tokens(simple_truncation) <= max_tokens:
            return simple_truncation

        # If simple truncation doesn't work, try more sophisticated approaches
        sentences = content.split('. ')
        if len(sentences) <= 1:
            # If it's just one sentence, simple truncation is our best bet
            return token_counter.truncate_text_to_tokens(content, max_tokens)

        # Try to build content by adding sentences until we reach the limit
        selected_content = ""
        for sentence in sentences:
            test_content = selected_content + ". " + sentence if selected_content else sentence
            if token_counter.count_tokens(test_content) <= max_tokens:
                selected_content = test_content
            else:
                # Add what we can of this sentence
                remaining_tokens = max_tokens - token_counter.count_tokens(selected_content)
                if remaining_tokens > 10:  # Worth adding partial sentence
                    partial_sentence = token_counter.truncate_text_to_tokens(sentence, remaining_tokens)
                    if partial_sentence.strip():
                        selected_content += ". " + partial_sentence
                break

        return selected_content.strip()

    def calculate_context_size(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        template: str = "Context: {context}\n\nQuestion: {query}\n\nPlease provide a helpful answer."
    ) -> Tuple[int, int, int]:
        """
        Calculate the token usage for a given set of chunks and query.

        Args:
            chunks: List of chunks to include in context
            query: The user query
            template: Template string for calculating context size

        Returns:
            Tuple of (context_tokens, query_tokens, total_tokens)
        """
        # Calculate context tokens
        context_content = "\n\n".join([chunk.content for chunk in chunks])
        context_tokens = token_counter.count_tokens(context_content)

        # Calculate query tokens
        query_tokens = token_counter.count_tokens(query)

        # Calculate template tokens (for formatting)
        template_tokens = token_counter.count_tokens(
            template.format(context="", query="")
        )

        total_tokens = context_tokens + query_tokens + template_tokens

        return context_tokens, query_tokens, total_tokens

    def trim_chunk_content(
        self,
        chunk: RetrievedChunk,
        max_tokens: int
    ) -> RetrievedChunk:
        """
        Trim a chunk's content to fit within a token limit.

        Args:
            chunk: The chunk to trim
            max_tokens: Maximum tokens allowed for the content

        Returns:
            A new chunk with trimmed content
        """
        if token_counter.count_tokens(chunk.content) <= max_tokens:
            return chunk

        trimmed_content = token_counter.truncate_text_to_tokens(chunk.content, max_tokens)
        trimmed_chunk = chunk.copy()
        trimmed_chunk.content = trimmed_content

        self.logger.info(
            f"Trimmed chunk {chunk.id} from {token_counter.count_tokens(chunk.content)} "
            f"to {token_counter.count_tokens(trimmed_chunk.content)} tokens"
        )

        return trimmed_chunk

    def prioritize_chunks_by_relevance(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        method: str = "score"
    ) -> List[RetrievedChunk]:
        """
        Prioritize chunks based on relevance to the query.

        Args:
            chunks: List of chunks to prioritize
            query: The user query
            method: Method for prioritization ('score', 'position', 'hybrid')

        Returns:
            List of chunks ordered by relevance
        """
        if method == "score":
            # Sort by similarity score (highest first)
            return sorted(
                chunks,
                key=lambda x: x.metadata.score or 0.0,
                reverse=True
            )
        elif method == "position":
            # Sort by position in document (earlier chunks first)
            return sorted(
                chunks,
                key=lambda x: x.metadata.chunk_index
            )
        elif method == "hybrid":
            # Hybrid approach: prioritize by score, then by position for ties
            return sorted(
                chunks,
                key=lambda x: (
                    x.metadata.score or 0.0,
                    -x.metadata.chunk_index  # Negative to prioritize earlier chunks
                ),
                reverse=True
            )
        else:
            # Default to score-based sorting
            return sorted(
                chunks,
                key=lambda x: x.metadata.score or 0.0,
                reverse=True
            )

    def optimize_context_for_query(
        self,
        request: OrchestrationRequest
    ) -> List[RetrievedChunk]:
        """
        Optimize the context for a given orchestration request.

        Args:
            request: The orchestration request containing query and chunks

        Returns:
            Optimized list of chunks that fit within context limits
        """
        # Select chunks based on relevance and token limits
        selected_chunks = self.select_chunks_for_context(
            chunks=request.retrieved_chunks,
            query=request.query,
            max_context_tokens=request.context_parameters.get('max_context_tokens'),
            max_chunks=request.max_chunks,
            min_similarity_score=request.min_similarity_score
        )

        # Further prioritize the selected chunks
        prioritized_chunks = self.prioritize_chunks_by_relevance(
            selected_chunks,
            request.query,
            method="hybrid"
        )

        return prioritized_chunks

    def validate_context_fits_model(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        max_context_tokens: Optional[int] = None
    ) -> bool:
        """
        Validate that the context will fit within the model's token limits.

        Args:
            chunks: List of chunks to validate
            query: The user query
            max_context_tokens: Maximum allowed tokens (defaults to settings)

        Returns:
            True if context fits within limits, False otherwise
        """
        if max_context_tokens is None:
            max_context_tokens = settings.LLM_MAX_TOKENS - 500  # Reserve for prompt and response

        _, _, total_tokens = self.calculate_context_size(chunks, query)

        return total_tokens <= max_context_tokens

    def get_context_summary(
        self,
        chunks: List[RetrievedChunk],
        query: str
    ) -> Dict[str, Any]:
        """
        Get a summary of the context including token usage and statistics.

        Args:
            chunks: List of chunks in the context
            query: The user query

        Returns:
            Dictionary with context summary information
        """
        context_tokens, query_tokens, total_tokens = self.calculate_context_size(chunks, query)

        # Calculate additional statistics
        avg_chunk_tokens = sum(token_counter.count_tokens(chunk.content) for chunk in chunks) / len(chunks) if chunks else 0
        avg_similarity_score = sum(
            chunk.metadata.score or 0.0 for chunk in chunks
        ) / len(chunks) if chunks else 0.0

        sources = list(set(chunk.metadata.source_file_path for chunk in chunks))

        return {
            "num_chunks": len(chunks),
            "num_sources": len(sources),
            "sources": sources,
            "context_tokens": context_tokens,
            "query_tokens": query_tokens,
            "total_tokens": total_tokens,
            "avg_chunk_tokens": avg_chunk_tokens,
            "avg_similarity_score": avg_similarity_score,
            "max_similarity_score": max((chunk.metadata.score or 0.0 for chunk in chunks), default=0.0),
            "min_similarity_score": min((chunk.metadata.score or 0.0 for chunk in chunks), default=0.0),
            "fits_model_context": total_tokens <= (settings.LLM_MAX_TOKENS - 500)
        }

    def apply_fallback_strategies(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        max_context_tokens: Optional[int] = None,
        strategy: str = "progressive_trimming"
    ) -> List[RetrievedChunk]:
        """
        Apply fallback strategies when context exceeds token limits.

        Args:
            chunks: List of chunks to apply fallback strategies to
            query: The user query
            max_context_tokens: Maximum tokens allowed for context (defaults to settings)
            strategy: Fallback strategy to use ('progressive_trimming', 'selective_ranking', 'query_focused', 'summary_based')

        Returns:
            List of chunks that fit within token limits using the chosen fallback strategy
        """
        if max_context_tokens is None:
            max_context_tokens = settings.LLM_MAX_TOKENS - 500  # Reserve for prompt and response

        # Check if the current chunks fit within limits
        current_context_tokens, query_tokens, total_tokens = self.calculate_context_size(chunks, query)

        if total_tokens <= max_context_tokens:
            # Context already fits, no fallback needed
            return chunks

        # Apply the chosen fallback strategy
        if strategy == "progressive_trimming":
            return self._apply_progressive_trimming_fallback(chunks, query, max_context_tokens)
        elif strategy == "selective_ranking":
            return self._apply_selective_ranking_fallback(chunks, query, max_context_tokens)
        elif strategy == "query_focused":
            return self._apply_query_focused_fallback(chunks, query, max_context_tokens)
        elif strategy == "summary_based":
            return self._apply_summary_based_fallback(chunks, query, max_context_tokens)
        else:
            # Default to progressive trimming
            return self._apply_progressive_trimming_fallback(chunks, query, max_context_tokens)

    def _apply_progressive_trimming_fallback(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        max_context_tokens: int
    ) -> List[RetrievedChunk]:
        """
        Apply progressive trimming fallback: gradually reduce content until it fits.

        Args:
            chunks: List of chunks to trim
            query: The user query
            max_context_tokens: Maximum tokens allowed

        Returns:
            List of trimmed chunks that fit within token limits
        """
        # First, try reducing the number of chunks
        for num_chunks in range(len(chunks), 0, -1):
            reduced_chunks = chunks[:num_chunks]
            _, _, total_tokens = self.calculate_context_size(reduced_chunks, query)

            if total_tokens <= max_context_tokens:
                return reduced_chunks

        # If reducing number of chunks isn't sufficient, try trimming content
        available_tokens = max_context_tokens - token_counter.count_tokens(query)
        template_tokens = token_counter.count_tokens("Context: \n\nQuestion: \n\nPlease provide a helpful answer.")
        available_tokens -= template_tokens

        # Try to proportionally reduce content in each chunk
        if available_tokens <= 0:
            return []

        # Calculate how much to reduce each chunk based on relative importance
        total_chunk_tokens = sum(token_counter.count_tokens(chunk.content) for chunk in chunks)
        reduction_ratio = available_tokens / total_chunk_tokens

        if reduction_ratio >= 1.0:
            return chunks

        # Trim each chunk according to the ratio
        trimmed_chunks = []
        used_tokens = 0

        for chunk in chunks:
            max_chunk_tokens = int(token_counter.count_tokens(chunk.content) * reduction_ratio)
            if used_tokens + max_chunk_tokens > available_tokens:
                max_chunk_tokens = available_tokens - used_tokens
                if max_chunk_tokens <= 0:
                    break

            trimmed_content = token_counter.truncate_text_to_tokens(chunk.content, max_chunk_tokens)
            if trimmed_content.strip():
                trimmed_chunk = chunk.copy()
                trimmed_chunk.content = trimmed_content
                trimmed_chunks.append(trimmed_chunk)
                used_tokens += token_counter.count_tokens(trimmed_content)

        return trimmed_chunks

    def _apply_selective_ranking_fallback(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        max_context_tokens: int
    ) -> List[RetrievedChunk]:
        """
        Apply selective ranking fallback: select only the most important chunks.

        Args:
            chunks: List of chunks to rank and select
            query: The user query
            max_context_tokens: Maximum tokens allowed

        Returns:
            List of selected chunks that fit within token limits
        """
        # Re-rank chunks with enhanced relevance scoring based on query
        enhanced_ranked_chunks = self._rank_chunks_intelligently(chunks, query)

        # Try to fit the most important chunks first
        selected_chunks = []
        used_tokens = 0

        for chunk in enhanced_ranked_chunks:
            chunk_tokens = token_counter.count_tokens(chunk.content)
            _, _, total_tokens = self.calculate_context_size(selected_chunks + [chunk], query)

            if total_tokens <= max_context_tokens:
                selected_chunks.append(chunk)
                used_tokens += chunk_tokens
            else:
                # Try to trim this chunk to see if we can fit it
                available_tokens = max_context_tokens - token_counter.count_tokens(query)
                template_tokens = token_counter.count_tokens("Context: \n\nQuestion: \n\nPlease provide a helpful answer.")
                available_tokens -= template_tokens - used_tokens

                if available_tokens > 50:  # Only worth trimming if we have significant space
                    trimmed_content = token_counter.truncate_text_to_tokens(chunk.content, available_tokens - used_tokens)
                    if trimmed_content.strip():
                        trimmed_chunk = chunk.copy()
                        trimmed_chunk.content = trimmed_content
                        selected_chunks.append(trimmed_chunk)

                break  # No more space for additional chunks

        return selected_chunks

    def _apply_query_focused_fallback(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        max_context_tokens: int
    ) -> List[RetrievedChunk]:
        """
        Apply query-focused fallback: prioritize chunks with query-related terms.

        Args:
            chunks: List of chunks to analyze
            query: The user query
            max_context_tokens: Maximum tokens allowed

        Returns:
            List of query-focused chunks that fit within token limits
        """
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        # Score chunks based on query relevance
        scored_chunks = []
        for chunk in chunks:
            content_lower = chunk.content.lower()

            # Calculate query relevance score
            term_matches = sum(1 for term in query_terms if term in content_lower)
            relevance_score = term_matches / len(query_terms) if query_terms else 0

            # Combine with similarity score
            combined_score = (relevance_score * 0.7) + ((chunk.metadata.score or 0.0) * 0.3)

            scored_chunks.append((chunk, combined_score))

        # Sort by combined relevance score
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Select chunks based on query relevance until token limit
        selected_chunks = []
        for chunk, score in scored_chunks:
            _, _, total_tokens = self.calculate_context_size(selected_chunks + [chunk], query)

            if total_tokens <= max_context_tokens:
                selected_chunks.append(chunk)
            else:
                # Try to trim this chunk to fit
                available_tokens = max_context_tokens - self.calculate_context_size(selected_chunks, query)[2]
                remaining_token_space = available_tokens - token_counter.count_tokens(chunk.content)

                if remaining_token_space > 0:
                    trimmed_content = token_counter.truncate_text_to_tokens(chunk.content, remaining_token_space)
                    if trimmed_content.strip():
                        trimmed_chunk = chunk.copy()
                        trimmed_chunk.content = trimmed_content
                        selected_chunks.append(trimmed_chunk)

                break  # No more space for additional chunks

        return selected_chunks

    def _apply_summary_based_fallback(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        max_context_tokens: int
    ) -> List[RetrievedChunk]:
        """
        Apply summary-based fallback: create a summary of content to fit within limits.

        Args:
            chunks: List of chunks to summarize
            query: The user query
            max_context_tokens: Maximum tokens allowed

        Returns:
            List with a single summarized chunk that fits within token limits
        """
        # This strategy would typically involve creating a summary of the content
        # For now, we'll implement a simple approach that combines key parts of each chunk
        combined_content = []

        # Add key information from each chunk - just the first few sentences to save tokens
        for chunk in chunks:
            sentences = chunk.content.split('. ')
            # Take only the first 1-2 sentences from each chunk to save tokens
            if len(sentences) >= 1:
                key_part = '. '.join(sentences[:2]) + '.'
                combined_content.append(key_part)

        # Combine all key parts
        summary_content = ' '.join(combined_content)

        # If the summary is still too long, truncate it
        _, query_tokens, base_tokens = self.calculate_context_size([], query)
        available_tokens = max_context_tokens - base_tokens

        if token_counter.count_tokens(summary_content) > available_tokens:
            summary_content = token_counter.truncate_text_to_tokens(summary_content, available_tokens)

        if not summary_content.strip():
            return []

        # Create a single summary chunk using the first chunk's metadata as a base
        summary_chunk = RetrievedChunk(
            id="summary-chunk",
            content=summary_content,
            metadata=chunks[0].metadata.copy() if chunks else ChunkMetadata(
                source_file_path="combined_sources",
                chunk_index=0,
                character_position=0,
                content_hash="summary_hash",
                original_content_length=len(summary_content),
                score=0.0
            )
        )

        return [summary_chunk]


def create_default_context_manager() -> ContextManager:
    """
    Create a default context manager instance.

    Returns:
        ContextManager: A new context manager instance
    """
    return ContextManager()


if __name__ == "__main__":
    # Example usage
    from src.models.orchestration_models import RetrievedChunk, ChunkMetadata

    print("Context Manager module loaded!")

    # Create sample chunks
    chunk1 = RetrievedChunk(
        id="chunk-1",
        content="The RAG system retrieves relevant documents from Qdrant vector database based on semantic similarity.",
        metadata=ChunkMetadata(
            source_file_path="docs/architecture.md",
            chunk_index=1,
            character_position=0,
            content_hash="hash1",
            original_content_length=100,
            score=0.85
        )
    )

    chunk2 = RetrievedChunk(
        id="chunk-2",
        content="It then uses a large language model to generate human-readable responses based on the retrieved context.",
        metadata=ChunkMetadata(
            source_file_path="docs/architecture.md",
            chunk_index=2,
            character_position=100,
            content_hash="hash2",
            original_content_length=100,
            score=0.78
        )
    )

    chunks = [chunk1, chunk2]
    query = "How does the RAG system work?"

    # Initialize context manager
    ctx_manager = ContextManager()

    # Select chunks for context
    selected = ctx_manager.select_chunks_for_context(chunks, query, max_context_tokens=1000)
    print(f"Selected {len(selected)} chunks for context")

    # Get context summary
    summary = ctx_manager.get_context_summary(selected, query)
    print(f"Context summary: {summary}")