# StudentOS RAG Microservice

A FastAPI microservice for processing PDF documents into chunked, embedded text ready for retrieval-augmented generation (RAG). This service handles PDF ingestion, markdown conversion, semantic chunking, and embedding generation for the StudentOS application.

## Architecture

The service acts as a processing pipeline between your Next.js application and the Supabase database:

```
Next.js App → FastAPI (PDF processing) → Next.js App → Supabase DB
```

### Workflow

1. **Next.js** sends PDF file + metadata to FastAPI
2. **FastAPI** processes the PDF:
   - Converts PDF to Markdown using `pymupdf4llm`
   - Chunks markdown semantically by headers
   - Generates 1536-dimensional embeddings using OpenAI
3. **FastAPI** returns structured chunks with embeddings
4. **Next.js** inserts chunks into Supabase using Drizzle ORM

## Features

- **High-Quality PDF Conversion**: Uses `pymupdf4llm` for accurate PDF → Markdown conversion optimized for LLMs
- **Semantic Chunking**: Intelligently splits by markdown headers (H1-H6) while respecting token limits
- **Embedding Generation**: OpenAI `text-embedding-3-small` with retry logic and exponential backoff
- **Structured Output**: Returns chunks ready for database insertion
- **Type Safety**: Full Pydantic validation for requests and responses
- **Error Handling**: Comprehensive logging and error recovery

## API Endpoints

### `POST /process-pdf`

Process a PDF file and return chunked, embedded data.

**Request (multipart/form-data):**
```
file: PDF file (required)
user_id: UUID (required)
file_name: string (required)
document_type: "syllabus" | "notes" | "other" (required)
course_id: UUID (optional)
```

**Response (application/json):**
```json
{
  "file_name": "example.pdf",
  "total_chunks": 15,
  "markdown_preview": "First 500 characters of markdown...",
  "chunks": [
    {
      "chunk_index": 0,
      "content": "# Introduction\nThis is the first section...",
      "embedding": [0.123, -0.456, ...],  // 1536 dimensions
      "metadata": {
        "heading": "Introduction",
        "section": "h1"
      }
    }
  ]
}
```

### `GET /health`

Health check endpoint with component status.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "pdf_converter": true,
    "markdown_chunker": true,
    "embedding_generator": true
  },
  "config": {
    "embedding_model": "text-embedding-3-small",
    "embedding_dimensions": 1536,
    "max_chunk_tokens": 500
  }
}
```

## Installation

### Prerequisites

- Python 3.13+
- OpenAI API key

### Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Run the service:**
   ```bash
   python main.py
   ```

   Or with uvicorn:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Configuration

Environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | **Required.** Your OpenAI API key |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `EMBEDDING_DIMENSIONS` | `1536` | Embedding vector dimensions |
| `MAX_CHUNK_TOKENS` | `500` | Maximum tokens per chunk |
| `CHUNK_OVERLAP_TOKENS` | `50` | Token overlap between chunks |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |

## Project Structure

```
student-os-rag/
├── main.py              # FastAPI application and endpoints
├── config.py            # Configuration settings
├── models.py            # Pydantic request/response models
├── pdf_converter.py     # PDF → Markdown conversion
├── chunker.py           # Semantic markdown chunking
├── embedder.py          # OpenAI embedding generation
├── pyproject.toml       # Dependencies and project metadata
├── .env.example         # Example environment configuration
└── README.md            # This file
```

## Integration with Next.js

Example Next.js integration:

```typescript
// actions/documents/process-pdf-rag.ts
export async function processPDFWithRAG(
  file: File,
  userId: string,
  documentType: string,
  courseId?: string
) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_id', userId);
  formData.append('file_name', file.name);
  formData.append('document_type', documentType);
  if (courseId) formData.append('course_id', courseId);

  const response = await fetch('http://localhost:8000/process-pdf', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();

  // Insert chunks into database using Drizzle
  await db.insert(documents).values(
    data.chunks.map((chunk) => ({
      id: uuidv4(),
      userId,
      courseId: courseId || null,
      documentType,
      fileName: data.file_name,
      chunkIndex: chunk.chunk_index,
      content: chunk.content,
      embedding: chunk.embedding,
      metadata: chunk.metadata,
      createdAt: new Date(),
      updatedAt: new Date(),
    }))
  );

  return data;
}
```

## Chunking Strategy

The service uses **semantic chunking by markdown headers**:

1. **Split by headers**: Documents are first split at H1-H6 headers
2. **Respect token limits**: Sections exceeding `MAX_CHUNK_TOKENS` are further split by paragraphs or sentences
3. **Preserve structure**: Header metadata (heading text, section level) is stored with each chunk
4. **Token estimation**: Uses word count × 1.3 (matches Next.js app)

This preserves document structure while ensuring chunks are appropriately sized for semantic search.

## Error Handling

- **PDF Conversion Failures**: Detailed error messages with stack traces
- **Rate Limiting**: Exponential backoff retry (2 retries by default)
- **Validation Errors**: 400 status codes with clear error messages
- **Server Errors**: 500 status codes with sanitized error details

All errors are logged with full context for debugging.

## Development

### Run in development mode:
```bash
uvicorn main:app --reload
```

### View API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Production Considerations

1. **CORS Configuration**: Update `allow_origins` in `main.py` to restrict allowed origins
2. **API Authentication**: Add authentication middleware for production use
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Monitoring**: Add monitoring/observability (e.g., Prometheus, DataDog)
5. **Scaling**: Consider horizontal scaling behind a load balancer
6. **Error Tracking**: Integrate error tracking (e.g., Sentry)

## License

Part of the StudentOS project.
