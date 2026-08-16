"""FastAPI entrypoint for the InnerSync AI backend (Production World).

Per ADR-001 this service only *loads* artifacts produced by `ml_pipeline/`. It
never trains, fits, or tunes a model.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api import assessments, auth

app = FastAPI(
    title="InnerSync AI",
    description=(
        "Explainable stress prediction and wellbeing support for university "
        "students. Not a diagnostic tool."
    ),
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(assessments.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe.

    Returns:
        A static status document.
    """
    return {"status": "ok"}
