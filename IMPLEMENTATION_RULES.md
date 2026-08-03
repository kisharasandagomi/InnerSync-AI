# Implementation Rules

Concrete, checkable rules that operationalise CLAUDE.md. When in doubt, this
file wins over general instinct; CLAUDE.md wins over this file on philosophy.

## Repo boundaries (hard rules)

- `ml_pipeline/` may import from `ml_pipeline/src/` only. It must never import
  from `backend/`.
- `backend/app/ml`, `app/nlp`, `app/explainability`, `app/recommendation` may
  only **load** artifacts from `ml_pipeline/artifacts/`. No `fit()`, `.train()`,
  `GridSearchCV`, or similar training calls are permitted anywhere under `backend/`.
- Any new model, encoder, or scaler must be trained in `ml_pipeline/`, saved to
  `ml_pipeline/artifacts/` with a version-stamped filename
  (e.g. `stress_model_v1.pkl`), and only then wired into the backend loader.
- Raw and processed data live only in `ml_pipeline/datasets/` (gitignored).
  Never commit a dataset file, even a small one.

## Database

- All schema changes go through `backend/alembic/` migrations. No manual `ALTER
  TABLE`, no editing the DB directly in production or staging.
- ORM models live in `backend/app/models/`. One model per file.
- Every model needs a matching Pydantic schema in `backend/app/schemas/` — never
  return an ORM object directly from an API route.

## ML / experiments

- Every experiment run (not just the winning model) is logged under
  `ml_pipeline/experiments/` with: model name, hyperparameters, all evaluation
  metrics (not just accuracy), and the dataset version used.
- Cross-validation is mandatory before any model is considered "final."
- Before saving a model as the production artifact, confirm: (1) performance was
  checked on a held-out/external validation set, not only CV folds on the
  training data; (2) SHAP values have been computed and sanity-checked against
  domain expectations (e.g. does high academic pressure push toward higher
  predicted stress, as expected).

## Explainability

- `explanation_generator.py` (backend) must never pass a raw SHAP value, feature
  name, or numeric weight into a user-facing string. If a change to this file
  would expose one, stop and flag it.
- Every human-readable explanation must be traceable back to the SHAP values
  that produced it, in a debug/log field the user never sees — for academic
  evaluation of explanation faithfulness later.

## Testing

- `backend/tests/`: every API route needs at least one happy-path test and one
  auth-failure test.
- `ml_pipeline/tests/`: every function in `src/preprocessing/` and
  `src/features/` needs a unit test, specifically checking for data leakage
  (e.g. that any scaler/encoder is fit only on training data, never on the
  full dataset before splitting).
- No PR/commit that touches `ml_pipeline/src/` merges without a passing test run.

## Code style

- Python: PEP8, type hints on all function signatures, docstrings in Google
  style (Args/Returns/Raises).
- No bare `except:` — catch specific exceptions.
- Config values (API keys, DB URLs, model paths) come from `.env` via
  `backend/app/core/config.py` — never hardcoded, never committed.

## Documentation

- Any architectural decision that changes a previous choice gets an entry in
  `docs/decisions/ADR.md` (short: context, decision, consequences).
- `docs/research/` files are the working source of truth for dissertation
  chapters. The submitted `.docx` is generated from these, not maintained as an
  independent copy.
