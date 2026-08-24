import httpx

from app.config import get_settings


class EmbeddingServiceError(RuntimeError):
    pass


def create_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    url = f"{settings.ollama_base_url.rstrip('/')}/api/embed"

    try:
        response = httpx.post(
            url,
            json={
                "model": settings.embedding_model,
                "input": texts,
                "truncate": True,
                "keep_alive": "10m",
            },
            timeout=120.0,
        )
        response.raise_for_status()

    except httpx.HTTPError as exc:
        raise EmbeddingServiceError(
            f"Ollama embedding request failed: {exc}"
        ) from exc

    embeddings = response.json().get("embeddings")

    if not isinstance(embeddings, list):
        raise EmbeddingServiceError(
            "Ollama returned invalid embeddings"
        )

    if len(embeddings) != len(texts):
        raise EmbeddingServiceError(
            "Ollama returned an invalid number of embeddings"
        )

    for embedding in embeddings:
        if len(embedding) != settings.embedding_dimensions:
            raise EmbeddingServiceError(
                "Unexpected embedding dimension: "
                f"expected {settings.embedding_dimensions}, "
                f"received {len(embedding)}"
            )

    return embeddings
