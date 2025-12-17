# Data Model: RAG Chatbot

**Feature**: 1-rag-chatbot
**Created**: 2025-12-16
**Version**: 1.0

## DocumentChunk

Represents a semantic piece of text extracted from source documentation.

### Attributes
- `id`: string (UUID) - Unique identifier for the chunk
- `text_content`: string - The actual text content of the chunk (max 512 tokens)
- `source_file_path`: string - Path to the original markdown file
- `chunk_index`: integer - Position of this chunk in the original document
- `character_position`: integer - Start position in original document
- `content_hash`: string - Hash for change detection
- `created_at`: datetime - Timestamp of creation
- `updated_at`: datetime - Timestamp of last update

### Validation Rules
- `text_content` must not exceed 512 tokens
- `source_file_path` must be a valid path reference
- `chunk_index` must be non-negative
- `character_position` must be non-negative

### State Transitions
- Created → Validated → Stored
- Stored → Updated (when source changes)
- Stored → Deleted (when source is removed)

## EmbeddingVector

A numerical representation of text content in high-dimensional space.

### Attributes
- `id`: string (UUID) - Unique identifier (corresponds to DocumentChunk.id)
- `vector`: array<float> - The embedding vector values (1024 dimensions for Cohere)
- `metadata`: object - JSON containing source file, chunk index, etc.
  - `source_file_path`: string
  - `chunk_index`: integer
  - `character_position`: integer
  - `content_hash`: string
- `collection_name`: string - Qdrant collection name ("myfirst_book")
- `created_at`: datetime - Timestamp of creation

### Validation Rules
- `vector` must have exactly 1024 elements (for Cohere multilingual model)
- `collection_name` must match configured collection
- `metadata` must contain required fields

## SourceFile

The original markdown document from which chunks are derived.

### Attributes
- `file_path`: string - Path to the source markdown file
- `last_modified`: datetime - Timestamp of last modification
- `content_hash`: string - Hash of file content for change detection
- `status`: enum - Processing status (pending, processed, failed)
- `chunks_count`: integer - Number of chunks created from this file
- `created_at`: datetime - Timestamp of first detection
- `updated_at`: datetime - Timestamp of last update

### Validation Rules
- `file_path` must be a valid markdown file path
- `status` must be one of: "pending", "processed", "failed"
- `chunks_count` must be non-negative

### State Transitions
- Detected → Pending → Processed
- Processed → Pending (when file changes)
- Pending → Failed (when processing errors occur)

## QuerySession

Represents a user's interaction session with the RAG system.

### Attributes
- `id`: string (UUID) - Unique identifier for the session
- `query_text`: string - The user's original query
- `response_text`: string - The system's response to the query
- `retrieved_chunks`: array<UUID> - IDs of chunks used in response
- `confidence_score`: float - Confidence level of the response (0.0-1.0)
- `created_at`: datetime - Timestamp of query
- `response_time_ms`: integer - Time taken to generate response

### Validation Rules
- `query_text` must not be empty
- `confidence_score` must be between 0.0 and 1.0
- `response_time_ms` must be positive