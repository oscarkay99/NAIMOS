from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    ai,
    analytics,
    audit,
    auth,
    evidence,
    field_reports,
    geo,
    incidents,
    reports,
    risk,
    satellite,
)
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="NAIMOS Intelligence API",
    description="AI-Assisted Illegal Mining Intelligence & Operations Platform - decision-support backend.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(incidents.router)
app.include_router(risk.router)
app.include_router(geo.router)
app.include_router(evidence.router)
app.include_router(field_reports.router)
app.include_router(ai.router)
app.include_router(reports.router)
app.include_router(analytics.router)
app.include_router(audit.router)
app.include_router(satellite.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "demo_mode": settings.demo_mode, "environment": settings.environment}
