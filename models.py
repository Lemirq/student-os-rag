from pydantic import BaseModel, Field
from typing import Optional


class DocumentChunk(BaseModel):
    """Represents a single chunk of a processed document."""

    chunk_index: int = Field(..., description="Sequential index of this chunk")
    content: str = Field(..., description="Text content of the chunk")
    embedding: list[float] = Field(..., description="1536-dimensional embedding vector")
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (pageNumber, section, heading, etc.)",
    )


class ProcessPDFRequest(BaseModel):
    """Request model for PDF processing."""

    file_name: str = Field(..., description="Original filename of the PDF")
    user_id: str = Field(..., description="UUID of the user uploading the document")
    course_id: Optional[str] = Field(
        None, description="Optional UUID of associated course"
    )
    document_type: str = Field(
        ...,
        description="Type of document: 'syllabus', 'notes', or 'other'",
        pattern="^(syllabus|notes|other)$",
    )


class ProcessPDFResponse(BaseModel):
    """Response model for PDF processing."""

    file_name: str
    total_chunks: int
    chunks: list[DocumentChunk]
    markdown_preview: str = Field(
        ..., description="First 500 characters of the converted markdown"
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None
