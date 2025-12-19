#!/usr/bin/env python3
"""
Test script to run a query through the orchestration layer
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.services.query_orchestrator import QueryOrchestratorService
from src.models.orchestration_models import OrchestrationRequest

async def test_orchestration():
    """Test the orchestration layer with a sample query"""
    print("Initializing Query Orchestrator Service...")

    # Check if required environment variables are set
    if not os.getenv("GEMINI_API_KEY"):
        print("Warning: GEMINI_API_KEY not set. This will cause the test to fail unless using mock.")

    if not os.getenv("COHERE_API_KEY"):
        print("Warning: COHERE_API_KEY not set. This will cause the test to fail unless using mock.")

    orchestrator = QueryOrchestratorService()

    # Create a sample request
    request = OrchestrationRequest(
        query="What is the RAG system architecture?",
        max_chunks=3,
        min_similarity_score=0.5,
        include_source_citations=True
    )

    print(f"Testing query: {request.query}")
    print("Processing query through orchestration layer...")

    try:
        response = await orchestrator.process_query(request)
        print(f"\nResponse Status: {response.status}")
        print(f"Answer: {response.answer[:200]}..." if len(response.answer) > 200 else f"Answer: {response.answer}")
        print(f"Sources: {len(response.sources)} source(s) found")
        print(f"Processing time: {response.total_time_ms:.2f}ms")
        print(f"Retrieval time: {response.retrieval_time_ms:.2f}ms")
        print(f"Generation time: {response.generation_time_ms:.2f}ms")

        if response.usage_metrics:
            print(f"Prompt tokens: {response.usage_metrics.prompt_tokens}")
            print(f"Completion tokens: {response.usage_metrics.completion_tokens}")
            print(f"Total tokens: {response.usage_metrics.total_tokens}")

        if response.sources:
            print("\nFirst source:")
            first_source = response.sources[0]
            print(f"  File: {first_source.source_file_path}")
            print(f"  Score: {first_source.similarity_score}")
            print(f"  Snippet: {first_source.snippet[:100]}...")

    except Exception as e:
        print(f"Error during orchestration: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing RAG orchestration system...")
    asyncio.run(test_orchestration())