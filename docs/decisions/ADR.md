# Architectural Decision Records

Short entries: context, decision, consequences. Add a new entry whenever an
architectural decision changes a previous choice (per `IMPLEMENTATION_RULES.md`).

## ADR-001: Research World / Production World separation

**Context**: The backend must never retrain or fit models — the dissertation's
research contribution lives in `ml_pipeline/`, and mixing training logic into
the production service would blur that boundary and risk data leakage between
research and serving code paths.

**Decision**: `ml_pipeline/` and `backend/app/` are physically separate.
`backend/app/{ml,nlp,explainability,recommendation}` only load versioned
artifacts from `ml_pipeline/artifacts/`; no `fit()`/`.train()` calls are
permitted under `backend/`.

**Consequences**: Any new model, encoder, or scaler must be trained in
`ml_pipeline/`, exported as a version-stamped artifact, and only then wired
into the backend loader. Slightly more friction per iteration, in exchange for
a clean, defensible boundary between research and delivery code.
