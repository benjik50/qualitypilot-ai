from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from app.config import get_settings


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def initialize_database() -> None:
    settings = get_settings()
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with psycopg.connect(
        settings.database_url,
        autocommit=True,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema_sql)


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    settings = get_settings()

    with psycopg.connect(settings.database_url) as connection:
        register_vector(connection)
        yield connection


def save_document(
    document_name: str,
    content_hash: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError(
            "The number of chunks must match the number of embeddings"
        )

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO documents (
                    name,
                    content_hash,
                    chunk_count
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (name)
                DO UPDATE SET
                    content_hash = EXCLUDED.content_hash,
                    chunk_count = EXCLUDED.chunk_count,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    document_name,
                    content_hash,
                    len(chunks),
                ),
            )

            document_row = cursor.fetchone()

            if document_row is None:
                raise RuntimeError("The document could not be saved")

            document_id = int(document_row["id"])

            cursor.execute(
                """
                DELETE FROM document_chunks
                WHERE document_id = %s
                """,
                (document_id,),
            )

            chunk_rows = [
                (
                    document_id,
                    chunk_index,
                    chunk,
                    Vector(embedding),
                )
                for chunk_index, (chunk, embedding) in enumerate(
                    zip(chunks, embeddings, strict=True)
                )
            ]

            cursor.executemany(
                """
                INSERT INTO document_chunks (
                    document_id,
                    chunk_index,
                    content,
                    embedding
                )
                VALUES (%s, %s, %s, %s)
                """,
                chunk_rows,
            )

    return document_id


def list_documents() -> list[dict]:
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    chunk_count,
                    content_hash,
                    created_at,
                    updated_at
                FROM documents
                ORDER BY updated_at DESC
                """
            )

            return [dict(row) for row in cursor.fetchall()]


def search_similar_chunks(
    query_embedding: list[float],
    limit: int,
) -> list[dict]:
    if not query_embedding:
        return []

    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    query_vector = Vector(query_embedding)

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    dc.id AS chunk_id,
                    d.name AS document_name,
                    dc.chunk_index,
                    dc.content,
                    (
                        1 - (dc.embedding <=> %s)
                    )::double precision AS similarity
                FROM document_chunks AS dc
                INNER JOIN documents AS d
                    ON d.id = dc.document_id
                ORDER BY dc.embedding <=> %s
                LIMIT %s
                """,
                (
                    query_vector,
                    query_vector,
                    limit,
                ),
            )

            return [dict(row) for row in cursor.fetchall()]