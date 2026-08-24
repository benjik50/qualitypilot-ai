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
        connection.execute(schema_sql)


def get_connection():
    connection = psycopg.connect(
        get_settings().database_url
    )
    register_vector(connection)
    return connection


def save_document(
    name: str,
    content_hash: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError(
            "Each chunk must have one embedding"
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:
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
                (name, content_hash, len(chunks)),
            )

            row = cursor.fetchone()

            if row is None:
                raise RuntimeError(
                    "PostgreSQL did not return the document id"
                )

            document_id = int(row[0])

            cursor.execute(
                """
                DELETE FROM document_chunks
                WHERE document_id = %s
                """,
                (document_id,),
            )

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
                [
                    (
                        document_id,
                        index,
                        chunk,
                        Vector(embedding),
                    )
                    for index, (chunk, embedding)
                    in enumerate(zip(chunks, embeddings))
                ],
            )

    return document_id


def list_documents() -> list[dict]:
    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
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

            return [
                dict(row)
                for row in cursor.fetchall()
            ]
