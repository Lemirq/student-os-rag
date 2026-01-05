import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from models import ProcessPDFResponse, DocumentChunk, ErrorResponse
from pdf_converter import PDFConverter
from chunker import MarkdownChunker
from embedder import EmbeddingGenerator
from auth import verify_api_key

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Global instances (initialized on startup)
pdf_converter: Optional[PDFConverter] = None
markdown_chunker: Optional[MarkdownChunker] = None
embedding_generator: Optional[EmbeddingGenerator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, clean up on shutdown."""
    global pdf_converter, markdown_chunker, embedding_generator

    logger.info("Initializing RAG microservice...")

    # Initialize components
    pdf_converter = PDFConverter()
    markdown_chunker = MarkdownChunker(
        max_tokens=settings.max_chunk_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    embedding_generator = EmbeddingGenerator()

    logger.info("RAG microservice initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down RAG microservice...")


app = FastAPI(
    title="StudentOS RAG Microservice",
    description="PDF ingestion, markdown conversion, chunking, and embedding generation",
    version="0.1.0",
    lifespan=lifespan,
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """Health check endpoint."""
    return {
        "service": "student-os-rag",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "components": {
            "pdf_converter": pdf_converter is not None,
            "markdown_chunker": markdown_chunker is not None,
            "embedding_generator": embedding_generator is not None,
        },
        "config": {
            "embedding_model": settings.embedding_model,
            "embedding_dimensions": settings.embedding_dimensions,
            "max_chunk_tokens": settings.max_chunk_tokens,
        },
    }


@app.post(
    "/process-pdf",
    response_model=ProcessPDFResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        403: {"model": ErrorResponse, "description": "Forbidden - Invalid API key"},
        429: {"model": ErrorResponse, "description": "Too many requests"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@limiter.limit(settings.rate_limit)
async def process_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF file to process"),
    user_id: str = Form(..., description="UUID of the user"),
    file_name: str = Form(..., description="Original filename"),
    document_type: str = Form(
        ..., description="Document type: 'syllabus', 'notes', or 'other'"
    ),
    course_id: Optional[str] = Form(None, description="Optional course UUID"),
    api_key: str = Depends(verify_api_key),
):
    """
    Process a PDF file: convert to markdown, chunk semantically, and generate embeddings.

    Returns structured chunks ready for database insertion by the Next.js app.
    """
    try:
        # Validate document type
        if document_type not in ["syllabus", "notes", "other"]:
            raise HTTPException(
                status_code=400,
                detail="document_type must be 'syllabus', 'notes', or 'other'",
            )

        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail="Only PDF files are supported"
            )

        logger.info(f"Processing PDF: {file_name} for user {user_id}")

        # Read PDF bytes
        pdf_bytes = await file.read()
        logger.info(f"Read {len(pdf_bytes)} bytes from {file_name}")

        # Convert PDF to Markdown
        markdown_text = await pdf_converter.convert_to_markdown(pdf_bytes, file_name)

        # Chunk the markdown semantically
        chunks = markdown_chunker.chunk(markdown_text)

        # Extract text content for embedding generation
        chunk_texts = [chunk["content"] for chunk in chunks]

        # Generate embeddings for all chunks
        embeddings = await embedding_generator.generate_embeddings(chunk_texts)

        # Build response with structured chunks
        document_chunks = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            document_chunks.append(
                DocumentChunk(
                    chunk_index=idx,
                    content=chunk["content"],
                    embedding=embedding,
                    metadata=chunk["metadata"],
                )
            )

        # Create markdown preview (first 500 chars)
        markdown_preview = (
            markdown_text[:500] + "..."
            if len(markdown_text) > 500
            else markdown_text
        )

        logger.info(
            f"Successfully processed {file_name}: "
            f"{len(document_chunks)} chunks created"
        )

        return ProcessPDFResponse(
            file_name=file_name,
            total_chunks=len(document_chunks),
            chunks=document_chunks,
            markdown_preview=markdown_preview,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF {file_name}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to process PDF: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )
