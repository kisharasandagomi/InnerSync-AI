# System Architecture

## Status

Not yet populated in full. Will document the Research World / Production
World separation (see `CLAUDE.md`), component boundaries, and data flow
between `ml_pipeline/`, `backend/app/`, and `frontend/`. One component is
documented below ahead of the rest, added in a later session.

## Progress Monitoring Dashboard (Module 9/10)

`frontend/src/pages/ProgressPage.tsx` reads `GET /assessments/history`
(`backend/app/api/assessments.py`) and renders a trend view over a
student's own check-ins. It introduces no new database table and no new
write path — it is a query over rows already written by the existing
predict → explain → recommend → adapt flow (`Assessment`,
`ExplanationRecord`, `Recommendation`), joined and reshaped read-only. See
`docs/architecture/api_design.md` for the endpoint contract and
`docs/research/methodology.md` § Progress Monitoring Dashboard for why it
shows trend framing (low/moderate/high, plain-language summaries) rather
than raw stress-level numbers or anything derived from SHAP.
