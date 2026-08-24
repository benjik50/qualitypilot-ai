from contextlib import asynccontextmanager
from datetime import datetime, timezone
from hashlib import sha256
import logging

import psycopg
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from app.chunking import split_text
from app.config import get_settings
from app.database import (
    initialize_database,
    list_documents,
    save_document,
)
from app.embeddings import (
    EmbeddingServiceError,
    create_embeddings,
)
from app.schemas import (
    DocumentSummary,
    IngestDocumentRequest,
    IngestDocumentResponse,
)


logger = logging.getLogger(__name__)


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
        "Copilote IA pour l'analyse de documents "
        "qualité fournisseur."
    ),
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/", tags=["General"])
async def root() -> dict[str, str]:
    return {
        "message": "Bienvenue sur QualityPilot AI",
        "documentation": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="qualitypilot-api",
        timestamp=datetime.now(timezone.utc),
    )


@app.post(
    "/documents/ingest",
    response_model=IngestDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["RAG"],
)
def ingest_document(
    payload: IngestDocumentRequest,
) -> IngestDocumentResponse:
    settings = get_settings()
    document_name = payload.document_name.strip()

    if not document_name:
        raise HTTPException(
            status_code=400,
            detail="document_name cannot be blank",
        )

    chunks = split_text(
        payload.text,
        settings.chunk_size,
        settings.chunk_overlap,
    )

    content_hash = sha256(
        payload.text.encode("utf-8")
    ).hexdigest()

    try:
        embeddings = create_embeddings(chunks)

        document_id = save_document(
            document_name,
            content_hash,
            chunks,
            embeddings,
        )

    except EmbeddingServiceError as exc:
        logger.exception("Embedding generation failed")

        raise HTTPException(
            status_code=502,
            detail="Ollama embedding service unavailable",
        ) from exc

    except psycopg.Error as exc:
        logger.exception("Document storage failed")

        raise HTTPException(
            status_code=503,
            detail="PostgreSQL unavailable",
        ) from exc

    return IngestDocumentResponse(
        document_id=document_id,
        document_name=document_name,
        chunk_count=len(chunks),
        embedding_model=settings.embedding_model,
        embedding_dimensions=(
            settings.embedding_dimensions
        ),
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
        logger.exception("Document listing failed")

        raise HTTPException(
            status_code=503,
            detail="PostgreSQL unavailable",
        ) from exc

    return [
        DocumentSummary.model_validate(document)
        for document in documents
    ]
