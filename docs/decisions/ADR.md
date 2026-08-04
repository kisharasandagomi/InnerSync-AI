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

## ADR-002: Local development moved to WSL2 Ubuntu

**Context**: The native Windows `mainks` conda environment could not import
compiled packages (pandas, lightgbm, etc.) — Windows Smart App Control was
blocking their DLLs, confirmed via Windows Event Log (`Microsoft-Windows-
CodeIntegrity/Operational`, Event ID 3077: "did not meet the Enterprise
signing level requirements") and reproduced with a bare `python -c "import
pandas"` outside Jupyter, ruling out a notebook/kernel-specific cause.
Smart App Control is a system-wide, one-way switch (cannot be disabled again
without reinstalling Windows once fully "On"), so disabling it was rejected
as a fix.

**Decision**: Migrated the whole Python/ML environment to WSL2 Ubuntu.
Installed Miniconda inside WSL and recreated `mainks` there via pip (pandas,
numpy, scikit-learn, xgboost, lightgbm, shap, matplotlib, seaborn, fastapi,
uvicorn, sqlalchemy, jupyter, python-jose, passlib, python-multipart,
python-dotenv, alembic, psycopg[binary]), plus `libgomp1` via `apt` to
resolve a LightGBM shared-library error. All imports now work inside WSL's
`mainks`. The project directory was copied from the Windows filesystem
(`/mnt/c/...`) into the WSL-native filesystem (`~/projects/InnerSync-AI`) to
avoid the performance and permission issues of working across the
Windows/Linux filesystem boundary.

**Consequences**: `environment.yml` has been regenerated from the WSL
env — package set differs slightly from the original Windows export (notably
`catboost`, `tensorflow`, `keras`, `scikeras`, `pytest`, `black`, `ruff`,
`plotly`, and `graphviz` are not yet reinstalled in WSL; add them back if/when
needed). Local development from now on happens inside WSL2 (VS Code
"WSL: Reopen Folder in WSL", `mainks` interpreter selected there), not native
Windows Python. The canonical copy of the repo is the WSL-native one; the
Windows-side copy under `/mnt/c/...` should be treated as stale once the WSL
copy is confirmed working.
