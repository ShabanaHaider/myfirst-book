# Agent Context for RAG Chatbot Feature

**Feature**: 1-rag-chatbot
**Created**: 2025-12-16

## Technologies Added
- Cohere API for embeddings
- Qdrant vector database
- AsyncIO for concurrent processing
- Markdown parsing libraries
- API rate limiting and circuit breaker patterns

## Key Concepts
- RAG (Retrieval-Augmented Generation) pipeline
- Document chunking with overlap
- Semantic search with vector similarity
- Content change detection and reprocessing
- Batch processing for efficiency

## Architecture Patterns
- ETL pipeline with validation checkpoints
- Producer-consumer async processing
- Circuit breaker with exponential backoff
- Local caching with content hash keys

## Configuration Parameters
- chunk_size_tokens: 512
- overlap_percentage: 20
- top_k_retrieval: 5
- similarity_threshold: 0.7