# API Design

## Status

Not yet populated in full. Will document FastAPI route contracts,
request/response schemas, and auth flow once `backend/` implementation
begins (Phase 6). One route is documented below ahead of the rest, since it
was added in a later session and its read-only contract is small enough to
capture here directly.

## `GET /assessments/history`

Read-only. Returns the authenticated caller's own past check-ins, oldest
first — no prediction, explanation, or recommendation logic runs on this
path; it reads back what `POST /assessments` already persisted. Powers the
Progress Monitoring Dashboard (see `docs/research/methodology.md` §
Progress Monitoring Dashboard for the design rationale).

- **Auth**: same bearer-token dependency as `POST /assessments`
  (`app.api.deps.get_current_user`). 401 if absent/invalid.
- **Scope**: filtered by `Assessment.user_id == current_user.id`; never
  returns another user's rows.
- **Response**: `list[AssessmentHistoryItem]` — see
  `backend/app/schemas/assessment.py`. Per item: `assessment_id`,
  `created_at`, `stress_level` (0/1/2), `stress_level_label`,
  `previous_engagement`, `adaptive_recovery_applied`, `is_escalation`, and
  `top_factor_phrase` (a pre-approved plain-language phrase, or `null`).
  Carries no SHAP value, raw feature name, or numeric severity score — the
  same vocabulary discipline as `POST /assessments`'s response.
- **Empty case**: a user with no check-ins yet gets `[]`, not an error.
