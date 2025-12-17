# RAG Chatbot - Running Instructions

This document explains how to run the RAG Chatbot system and populate Qdrant with your documents.

## Prerequisites

1. **Python 3.9+** installed on your system
2. **Qdrant database** running (either local or cloud)
3. **API keys** for Cohere and Qdrant

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
Update the `.env` file with your actual API keys:

```env
# RAG Chatbot Configuration
COHERE_API_KEY=your_actual_cohere_api_key_here
QDRANT_URL=your_qdrant_url_here  # Or leave empty if using local Qdrant
QDRANT_API_KEY=your_qdrant_api_key_here  # Only needed if using Qdrant Cloud
QDRANT_HOST=localhost  # Use 'localhost' for local Qdrant, or your server address
QDRANT_PORT=6333  # Default Qdrant port
DOCS_DIRECTORY=my-book/docs/  # Directory containing your markdown documents
```

## Running Qdrant

### Option 1: Local Qdrant (Recommended for development)
```bash
# Using Docker
docker run -p 6333:6333 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

### Option 2: Qdrant Cloud
- Sign up at [qdrant.tech](https://qdrant.tech)
- Create a collection
- Use the provided URL and API key in your `.env` file

## Running the Ingestion Process

Once Qdrant is running and your `.env` file is configured, run the ingestion:

```bash
python run_ingestion.py
```

This will:
1. Connect to Qdrant
2. Scan the documents directory for markdown files
3. Process and chunk the documents
4. Generate embeddings using Cohere
5. Store the vectors in Qdrant
6. Verify that data is available

## Running a Sample Query

After successful ingestion, you can test querying:

```bash
python -c "
import asyncio
from src.api.query_endpoint import QueryEndpoint

async def test_query():
    query_endpoint = QueryEndpoint()
    result = await query_endpoint.process_query({
        'query': 'What is this book about?',
        'top_k': 3,
        'similarity_threshold': 0.7
    })
    print('Query result:', result)

asyncio.run(test_query())
"
```

## Verifying Data in Qdrant

To check if your data is available in Qdrant:

```bash
python check_qdrant_data.py
```

## Troubleshooting

### Common Issues:

1. **"ModuleNotFoundError: No module named 'qdrant_client'"**
   - Run: `pip install -r requirements.txt`

2. **"Failed to connect to Qdrant"**
   - Verify Qdrant is running
   - Check your QDRANT_URL, QDRANT_HOST, QDRANT_PORT, and QDRANT_API_KEY settings

3. **"COHERE_API_KEY is required"**
   - Make sure you've set your Cohere API key in the `.env` file

4. **No documents found**
   - Verify that your `DOCS_DIRECTORY` contains markdown (.md) files
   - Check that the directory path is correct in your `.env` file

5. **Rate limit exceeded**
   - Cohere API has rate limits; wait before making more requests
   - Consider upgrading your Cohere plan for higher limits

### Environment Variables:

- `COHERE_API_KEY`: Your Cohere API key for generating embeddings
- `QDRANT_URL`: Full URL to Qdrant Cloud instance (optional if using local)
- `QDRANT_API_KEY`: API key for Qdrant Cloud (optional if using local)
- `QDRANT_HOST`: Host for local Qdrant (default: localhost)
- `QDRANT_PORT`: Port for local Qdrant (default: 6333)
- `DOCS_DIRECTORY`: Directory containing markdown documents to ingest
- `COLLECTION_NAME`: Qdrant collection name (default: myfirst_book)
- `CHUNK_SIZE_TOKENS`: Maximum tokens per document chunk (default: 512)
- `TOP_K_RETRIEVAL`: Number of similar documents to retrieve (default: 5)

## Next Steps

After successful ingestion:

1. Test queries to ensure the system works
2. Adjust configuration parameters as needed
3. Add more documents to your `DOCS_DIRECTORY`
4. Run incremental ingestion to update with new/changed documents