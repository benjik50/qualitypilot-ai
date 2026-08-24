from datetime import datetime

from pydantic import BaseModel, Field


class IngestDocumentRequest(BaseModel):
    document_name: str = Field(
        min_length=1,
        max_length=255,
    )
    text: str = Field(min_length=20)


class IngestDocumentResponse(BaseModel):
    document_id: int
    document_name: str
    chunk_count: int
    embedding_model: str
    embedding_dimensions: int


class DocumentSummary(BaseModel):
    id: int
    name: str
    chunk_count: int
    content_hash: str
    created_at: datetime
    updated_at: datetime
