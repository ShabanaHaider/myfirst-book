"""
Prompt Template Models for RAG Chatbot

This module defines data models for prompt templates used in the orchestration layer.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum
import json


class PromptRole(str, Enum):
    """Enumeration of different roles in a prompt conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    CONTEXT = "context"


class PromptTemplate(BaseModel):
    """
    Base model for prompt templates.
    Defines the structure and formatting for different types of prompts.
    """
    template_id: str = Field(..., description="Unique identifier for the template")
    name: str = Field(..., description="Human-readable name for the template")
    description: str = Field("", description="Description of what the template is for")
    system_message: str = Field("", description="System message to guide the model")
    context_format: str = Field("", description="Format string for context chunks")
    query_format: str = Field("", description="Format string for user queries")
    response_format: str = Field("", description="Expected format of the response")
    default_parameters: Dict[str, Any] = Field(default_factory=dict, description="Default parameters for the template")
    max_context_tokens: Optional[int] = Field(None, description="Maximum tokens for context")
    requires_context: bool = Field(True, description="Whether the template requires context")

    def format_prompt(self, query: str, context: List[Dict[str, Any]] = None, **kwargs) -> List[Dict[str, str]]:
        """
        Format the prompt with the given query and context.

        Args:
            query: The user's query
            context: List of context chunks
            **kwargs: Additional parameters to format the template

        Returns:
            List of message dictionaries ready to send to the LLM
        """
        messages = []

        # Add system message if present
        if self.system_message:
            system_msg = self.system_message.format(**kwargs)
            messages.append({"role": PromptRole.SYSTEM.value, "content": system_msg})

        # Add context if provided and required
        if context and self.requires_context:
            context_str = ""
            for chunk in context:
                if isinstance(chunk, dict):
                    chunk_content = chunk.get('content', chunk.get('text_content', ''))
                else:
                    chunk_content = str(chunk)

                formatted_chunk = self.context_format.format(context=chunk_content, **kwargs)
                context_str += formatted_chunk + "\n\n"

            if context_str.strip():
                messages.append({"role": PromptRole.CONTEXT.value, "content": context_str.strip()})

        # Add user query
        formatted_query = self.query_format.format(query=query, context=context_str if context else "", **kwargs)
        messages.append({"role": PromptRole.USER.value, "content": formatted_query})

        return messages

    def get_context_length(self, context: List[Dict[str, Any]], **kwargs) -> int:
        """
        Calculate the token length of the formatted context.

        Args:
            context: List of context chunks
            **kwargs: Additional parameters

        Returns:
            Number of tokens in the formatted context
        """
        if not context or not self.requires_context:
            return 0

        context_str = ""
        for chunk in context:
            if isinstance(chunk, dict):
                chunk_content = chunk.get('content', chunk.get('text_content', ''))
            else:
                chunk_content = str(chunk)

            formatted_chunk = self.context_format.format(context=chunk_content, **kwargs)
            context_str += formatted_chunk + "\n\n"

        # We'll calculate tokens in the calling code since we don't have access to the token counter here
        return len(context_str)


class RAGPromptTemplate(PromptTemplate):
    """
    Specialized prompt template for RAG (Retrieval-Augmented Generation) scenarios.
    """
    template_id: str = "rag-default"
    name: str = "RAG Default Template"
    description: str = "Default template for RAG scenarios with context and query"
    system_message: str = (
        "You are a helpful AI assistant for the myfirst_book documentation. "
        "Use the provided context to answer questions accurately. "
        "If the context doesn't contain the information needed to answer, say so. "
        "Be concise but comprehensive in your responses."
    )
    context_format: str = "Context: {context}"
    query_format: str = "Question: {query}\n\nBased on the context above, please provide a helpful and accurate answer."
    response_format: str = "A clear, concise answer based on the provided context"
    max_context_tokens: Optional[int] = 2000
    requires_context: bool = True


class SimpleQueryTemplate(PromptTemplate):
    """
    Simple query template without context, for general questions.
    """
    template_id: str = "simple-query"
    name: str = "Simple Query Template"
    description: str = "Template for simple queries without context"
    system_message: str = (
        "You are a helpful AI assistant. Answer the user's question to the best of your ability."
    )
    context_format: str = ""
    query_format: str = "{query}"
    response_format: str = "A helpful response to the user's query"
    requires_context: bool = False


class SummarizationTemplate(PromptTemplate):
    """
    Template for summarizing content.
    """
    template_id: str = "summarization"
    name: str = "Summarization Template"
    description: str = "Template for summarizing content"
    system_message: str = (
        "You are an expert content summarizer. Create a concise summary of the provided content."
    )
    context_format: str = "Content to summarize: {context}"
    query_format: str = "Please create a summary of the content above."
    response_format: str = "A concise summary of the provided content"
    max_context_tokens: Optional[int] = 3000
    requires_context: bool = True


class QAExtractionTemplate(PromptTemplate):
    """
    Template for extracting Q&A pairs from content.
    """
    template_id: str = "qa-extraction"
    name: str = "Q&A Extraction Template"
    description: str = "Template for extracting question-answer pairs from content"
    system_message: str = (
        "You are an expert at creating question-answer pairs from content. "
        "Extract 3-5 relevant Q&A pairs from the provided content."
    )
    context_format: str = "Content: {context}"
    query_format: str = ("Extract question-answer pairs from the content above. "
                         "Format as: Q: [question]\nA: [answer]\n\nQ: [question]\nA: [answer]")
    response_format: str = "Question-answer pairs extracted from the content"
    max_context_tokens: Optional[int] = 2500
    requires_context: bool = True


def get_default_rag_template() -> RAGPromptTemplate:
    """
    Get the default RAG prompt template.

    Returns:
        RAGPromptTemplate: The default RAG template
    """
    return RAGPromptTemplate()


def get_template_by_id(template_id: str) -> Optional[PromptTemplate]:
    """
    Get a prompt template by its ID.

    Args:
        template_id: The ID of the template to retrieve

    Returns:
        The prompt template if found, None otherwise
    """
    templates = {
        "rag-default": RAGPromptTemplate(),
        "simple-query": SimpleQueryTemplate(),
        "summarization": SummarizationTemplate(),
        "qa-extraction": QAExtractionTemplate(),
    }

    return templates.get(template_id)


def format_rag_prompt(query: str, context: List[Dict[str, Any]],
                     template: PromptTemplate = None) -> List[Dict[str, str]]:
    """
    Convenience function to format a RAG prompt.

    Args:
        query: The user's query
        context: List of context chunks
        template: The prompt template to use (defaults to default RAG template)

    Returns:
        List of message dictionaries ready to send to the LLM
    """
    if template is None:
        template = get_default_rag_template()

    return template.format_prompt(query=query, context=context)


if __name__ == "__main__":
    # Example usage
    print("Prompt Templates module loaded!")

    # Create a default RAG template
    rag_template = get_default_rag_template()
    print(f"Default template: {rag_template.name}")

    # Example context
    context = [
        {"content": "The RAG Chatbot system retrieves relevant documents from Qdrant vector database."},
        {"content": "It then uses a large language model to generate human-readable responses."}
    ]

    # Format a prompt
    query = "How does the RAG system work?"
    messages = format_rag_prompt(query, context)

    print(f"Formatted prompt has {len(messages)} messages")
    for i, msg in enumerate(messages):
        print(f"Message {i+1} ({msg['role']}): {msg['content'][:100]}...")