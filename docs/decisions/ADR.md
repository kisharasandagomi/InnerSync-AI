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

## ADR-003: Exclude six features from model training on target-leakage evidence

**Context**: SHAP analysis of the v1 model (`04_SHAPAnalysis.ipynb`) showed
`blood_pressure` carrying more than double the mean |SHAP| of any other
feature, despite EDA having ranked it the *weakest* linearly-correlated
feature (r = +0.394). Investigation found a near-deterministic,
non-monotonic mapping to the label — invisible to Pearson correlation, which
is why the EDA heatmap and the VIF check both passed it.

A systematic audit of all 20 features (`02_Preprocessing.ipynb` § Systematic
Target-Leakage Audit) established the problem was not confined to that one
column. Using a single-feature lookup test (a "most common class per value"
rule fit on the training split, scored on the held-out test set):

- `sleep_quality` alone: 0.9045 accuracy
- `future_career_concerns` alone: 0.9000
- `blood_pressure` alone: 0.8864
- `depression`, `bullying`, `anxiety_level`: 0.8773–0.8818
- Tuned 20-feature Random Forest, for reference: **0.8864**

Two single features beat the entire tuned model; six rival it. Every feature
shares one generative signature: a small near-uniform bucket at value 0
(behaving like a missing-data sentinel), with all other values mapping to a
single class at 85–100% purity. A single self-reported 0–5 item cannot
genuinely predict another self-reported item at 90% accuracy across three
balanced classes. The dataset appears to have been generated with features
sampled conditional on the label.

**Decision**: exclude the six features whose lookup-rule accuracy rivals the
full model — `sleep_quality`, `future_career_concerns`, `blood_pressure`,
`depression`, `bullying`, `anxiety_level` — and retrain. The full five-model
comparison was re-run on the remaining 14 features with split, CV strategy,
search grids and tuning objective held identical, and model selection was
re-derived from scratch (Random Forest re-selected: ROC-AUC 0.9838, F1
0.8815, only candidate without an adverse CV-to-test gap).

Artifacts were exported as **v2** rather than overwriting `stress_model_v1.pkl`.
Overwriting would have left the already-committed `artifact_manifest.json` —
which records v1's SHA-256 and 20-feature schema — describing a model that no
longer exists, defeating the version-stamping requirement in
`IMPLEMENTATION_RULES.md`. The original v1 results, notebooks sections, and
experiment logs are all retained rather than rewritten, so the discovery
sequence remains auditable.

**Consequences**:

- Exclusion cost only **0.0046 accuracy** (0.8864 → 0.8818). This is
  evidence that the decision did *not* fix the underlying problem, not
  evidence that the model survived it intact.
- **Feature removal is explicitly not a remedy for this dataset.** Dropping
  the three worst offenders costs zero accuracy; the six weakest features
  alone still yield 0.85 against a 0.333 chance baseline. Label information
  is redundantly encoded across essentially all columns, so excluding any
  subset shifts the model onto the next proxy. No further exclusion rounds
  should be attempted on this basis — the correct response is external data,
  not more pruning.
- No accuracy figure computed on this dataset, v1 or v2, may be presented as
  evidence of real-world predictive capability. The Phase 8
  externally-collected validation set is promoted from a strengthening step
  to the only route to an empirical performance claim.
- `backend/app/` must load the v2 artifacts (14-feature `feature_schema.json`
  and `shap_config.json`). Any inference code written against the v1
  20-feature contract will not work and must not be carried forward.
- Methodologically this strengthens rather than weakens the project: the
  explainability layer detected a data defect that correlation analysis, VIF,
  cross-validation and held-out testing had all passed over. See
  `methodology.md` § Data Quality / Leakage Finding for the connection to the
  Tariq et al. (2025) retraction discussed in Chapter 2.
