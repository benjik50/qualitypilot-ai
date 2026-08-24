from datetime import datetime

from pydantic import BaseModel, Field


class IngestDocumentRequest(BaseModel):
    document_name: str = Field(
        min_length=1,
        max_length=255,
    )
    text: str = Field(min_length=1)


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


class AskRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=2000,
        description="Question posée au système RAG",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Nombre de passages à récupérer",
    )


class SourceChunk(BaseModel):
    document_name: str
    chunk_index: int
    content: str
    similarity: float


class AskResponse(BaseModel):
    question: str
    answer: str
    chat_model: str
    sources: list[SourceChunk]