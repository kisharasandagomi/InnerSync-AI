"""Research World package.

Exists so `backend/` can import the explanation and recommendation logic as
`ml_pipeline.src.*` rather than duplicating it (ADR-001 permits the backend to
*load* research-world artifacts and pure functions; it must never train).
"""
