from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


app = FastAPI(
    title="QualityPilot AI",
    description="Copilote IA pour l'analyse de documents qualité fournisseur.",
    version="0.1.0",
)


@app.get("/", tags=["General"])
async def root() -> dict[str, str]:
    return {
        "message": "Bienvenue sur QualityPilot AI",
        "documentation": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="qualitypilot-api",
        timestamp=datetime.now(timezone.utc),
    )
