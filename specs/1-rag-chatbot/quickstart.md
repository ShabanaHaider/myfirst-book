# Quickstart Guide: RAG Chatbot for myfirst_book

**Feature**: 1-rag-chatbot
**Created**: 2025-12-16

## Prerequisites

1. Python 3.9+ installed
2. Cohere API key
3. Qdrant database (local or cloud)
4. Access to `my_book/docs/` directory with markdown files

## Installation

1. Install required dependencies:
```bash
pip install cohere qdrant-client markdown beautifulsoup4 python-dotenv asyncio aiohttp
```

2. Set up environment variables:
Create a `.env` file with:
```
COHERE_API_KEY=your_cohere_api_key_here
QDRANT_URL=your_qdrant_url_here
QDRANT_API_KEY=your_qdrant_api_key_here  # if using cloud
```

## Basic Setup

1. Initialize the RAG system:
```python
from rag_chatbot import RAGSystem

rag_system = RAGSystem.from_config({
    "cohere_api_key": os.getenv("COHERE_API_KEY"),
    "qdrant_url": os.getenv("QDRANT_URL"),
    "qdrant_api_key": os.getenv("QDRANT_API_KEY"),
    "docs_directory": "my_book/docs/",
    "collection_name": "myfirst_book"
})
```

2. Run initial ingestion:
```python
# Process all markdown files in the docs directory
job_id = rag_system.ingest_documents(force_reprocess=True)
print(f"Ingestion started with job ID: {job_id}")

# Check status
status = rag_system.get_ingestion_status(job_id)
print(f"Progress: {status['progress']['percentage']}%")
```

## Query Examples

1. Basic query:
```python
response = rag_system.query("What are the main concepts in the book?")
print(response.text)
print(f"Sources: {response.sources}")
```

2. Advanced query with parameters:
```python
response = rag_system.query(
    query="Explain the key principles of humanoid robotics",
    top_k=5,
    similarity_threshold=0.7,
    include_sources=True
)
```

## Configuration Options

- `chunk_size_tokens`: Maximum tokens per chunk (default: 512)
- `overlap_percentage`: Overlap between chunks (default: 20%)
- `top_k_retrieval`: Number of chunks to retrieve (default: 5)
- `similarity_threshold`: Minimum similarity score (default: 0.7)

## Common Operations

1. Check system health:
```python
health = rag_system.health_check()
print(health)
```

2. Get current configuration:
```python
config = rag_system.get_config()
print(config)
```

3. Re-process changed documents:
```python
# Only processes documents that have changed
job_id = rag_system.ingest_documents(force_reprocess=False)
```

## Troubleshooting

- If ingestion fails, check that the docs directory exists and contains markdown files
- If queries return no results, verify the vector database is populated and accessible
- If API calls fail, confirm API keys are valid and rate limits aren't exceeded