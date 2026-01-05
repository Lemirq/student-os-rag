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

## Security

The RAG microservice implements multiple security layers to ensure only your Next.js application can access it:

### API Key Authentication

All requests to `/process-pdf` require a valid API key in the `X-API-Key` header.

```bash
curl -X POST http://localhost:8000/process-pdf \
  -H "X-API-Key: your_secure_api_key_here" \
  -F "file=@document.pdf" \
  -F "user_id=uuid" \
  -F "file_name=document.pdf" \
  -F "document_type=notes"
```

**Security Features:**
- ✅ API key stored in environment variables
- ✅ Never exposed to browser/client
- ✅ Server-to-server authentication only
- ✅ Returns `403 Forbidden` for invalid keys

### Rate Limiting

Prevents abuse by limiting requests per IP address:
- **Default**: 10 requests per minute
- **Configurable**: Set `RATE_LIMIT` in `.env`
- **Response**: `429 Too Many Requests` when exceeded

### Server-to-Server Communication

The API key is **never** exposed to end users:

```
User Browser → Next.js Server Action (has API key) → FastAPI RAG Service
```

**NOT:**
```
User Browser (exposed key ❌) → FastAPI RAG Service
```

The Next.js Server Action (`"use server"`) runs on the server and handles the API key securely.

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

   # Generate a secure API key
   python -c "import secrets; print(secrets.token_urlsafe(32))"

   # Edit .env and add:
   # - OPENAI_API_KEY (your OpenAI API key)
   # - API_KEY (the generated secure key from above)
   ```

   **Important:** Copy the same `API_KEY` to your Next.js `.env.local` as `RAG_API_KEY`

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

## Deployment to Vercel

This service can be deployed to Vercel as a serverless function.

### 1. Deploy to Vercel

```bash
# Install Vercel CLI (if not already installed)
npm i -g vercel

# Deploy
vercel

# Or deploy to production
vercel --prod
```

### 2. Configure Environment Variables in Vercel

In your Vercel project settings, add these environment variables:

| Variable | Value | Required |
|----------|-------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | ✅ Yes |
| `API_KEY` | Your generated secure API key | ✅ Yes |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Optional (has default) |
| `EMBEDDING_DIMENSIONS` | `1536` | Optional (has default) |
| `MAX_CHUNK_TOKENS` | `500` | Optional (has default) |
| `CHUNK_OVERLAP_TOKENS` | `50` | Optional (has default) |
| `RATE_LIMIT` | `10/minute` | Optional (has default) |

**Important:** The `API_KEY` must match the `RAG_API_KEY` in your Next.js app's environment variables.

### 3. Update Next.js Environment Variable

After deployment, update your Next.js `.env.local` or Vercel environment variables:

```bash
RAG_API_URL=https://your-rag-service.vercel.app
RAG_API_KEY=your_secure_api_key_here
```

### 4. Vercel Build Settings

The project is pre-configured with:
- **Framework Preset**: Other
- **Build Command**: (uses vercel.json)
- **Install Command**: `pip install uv && uv sync`
- **Output Directory**: N/A (handled by vercel.json)

### Serverless Architecture

The Vercel deployment uses:
- **Handler**: `api/index.py` (Mangum wrapper)
- **Runtime**: Python 3.12 (Vercel's latest supported version)
- **Concurrency**: Auto-scaling serverless functions
- **Cold Start**: Components initialized on first request

**Note**: First request after deployment may take longer due to cold start.

## Production Considerations

1. **CORS Configuration**: Update `allow_origins` in `main.py` to restrict allowed origins
2. **API Authentication**: Add authentication middleware for production use
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Monitoring**: Add monitoring/observability (e.g., Prometheus, DataDog)
5. **Scaling**: Consider horizontal scaling behind a load balancer
6. **Error Tracking**: Integrate error tracking (e.g., Sentry)

## License

Part of the StudentOS project.
