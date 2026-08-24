from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib

import psycopg
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.chunking import split_text
from app.config import get_settings
from app.database import (
    initialize_database,
    list_documents,
    save_document,
    search_similar_chunks,
)
from app.embeddings import (
    EmbeddingServiceError,
    create_embeddings,
)
from app.llm import ChatServiceError, generate_answer
from app.schemas import (
    AskRequest,
    AskResponse,
    DocumentSummary,
    IngestDocumentRequest,
    IngestDocumentResponse,
    SourceChunk,
)


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="QualityPilot AI",
    description=(
        "Copilote IA utilisant Ollama, PostgreSQL, pgvector "
        "et une architecture RAG."
    ),
    version="0.3.0",
    lifespan=lifespan,
    default_response_class=UTF8JSONResponse,
)


@app.get("/", tags=["General"])
def root() -> dict[str, str]:
    return {
        "message": "Bienvenue sur QualityPilot AI",
        "documentation": "/docs",
        "health": "/health",
        "ask": "/ask",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="qualitypilot-api",
        timestamp=datetime.now(timezone.utc),
    )


@app.post(
    "/documents/ingest",
    response_model=IngestDocumentResponse,
    tags=["RAG"],
)
def ingest_document(
    payload: IngestDocumentRequest,
) -> IngestDocumentResponse:
    settings = get_settings()

    chunks = split_text(
        text=payload.text,
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The document does not contain usable text",
        )

    content_hash = hashlib.sha256(
        payload.text.encode("utf-8")
    ).hexdigest()

    try:
        embeddings = create_embeddings(chunks)

        document_id = save_document(
            document_name=payload.document_name,
            content_hash=content_hash,
            chunks=chunks,
            embeddings=embeddings,
        )

    except EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database operation failed: {exc}",
        ) from exc

    return IngestDocumentResponse(
        document_id=document_id,
        document_name=payload.document_name,
        chunk_count=len(chunks),
        embedding_model=settings.embedding_model,
        embedding_dimensions=settings.embedding_dimensions,
    )


@app.get(
    "/documents",
    response_model=list[DocumentSummary],
    tags=["RAG"],
)
def get_documents() -> list[DocumentSummary]:
    try:
        documents = list_documents()

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database operation failed: {exc}",
        ) from exc

    return [
        DocumentSummary.model_validate(document)
        for document in documents
    ]


@app.post(
    "/ask",
    response_model=AskResponse,
    tags=["RAG"],
)
def ask_question(payload: AskRequest) -> AskResponse:
    settings = get_settings()

    try:
        question_embedding = create_embeddings(
            [payload.question]
        )[0]

        sources = search_similar_chunks(
            query_embedding=question_embedding,
            limit=payload.top_k,
        )

        answer = generate_answer(
            question=payload.question,
            sources=sources,
        )

    except (EmbeddingServiceError, ChatServiceError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database operation failed: {exc}",
        ) from exc

    return AskResponse(
        question=payload.question,
        answer=answer,
        chat_model=settings.chat_model,
        sources=[
            SourceChunk.model_validate(source)
            for source in sources
        ],
    )