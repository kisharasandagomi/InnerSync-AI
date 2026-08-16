# Alembic migrations

## Status: initial revision generated and applied

`env.py` reads `DATABASE_URL` from `backend/.env` via `app.core.config`, so no
credential is ever written into a committed file. `backend/.env` itself is
gitignored.

**Applied revision:** `050a644df84f_initial_schema` — creates `users`,
`user_profiles`, `assessments`, `explanation_records`, `recommendations`.

Verified against PostgreSQL 18.4 (running inside WSL, database `innersync`):

- all five tables created, plus `alembic_version` at `050a644df84f`;
- `assessments` carries 20 columns, including the 14 model features in
  `feature_schema.json` order;
- the three JSON columns (`predicted_probabilities`, `faithfulness_factors`,
  `actions`) are genuine `JSONB`, and round-trip as `dict`/`list` rather than
  opaque strings — confirmed with a server-side JSONB query
  (`faithfulness_factors->0->>'feature'`).

## Recreating from scratch

```bash
cd backend
cp .env.example .env            # then fill in DATABASE_URL and JWT_SECRET_KEY
alembic upgrade head
```

## After changing a model

Never hand-edit a table. Add a revision:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Note on the test suite

`backend/tests/` runs against in-memory SQLite for speed and isolation, so it
does **not** exercise these migrations or the `JSONB` variant. Those are
verified separately against PostgreSQL as described above.
