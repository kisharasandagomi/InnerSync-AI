# InnerSync AI — frontend

React + TypeScript + Vite + Tailwind. Calls the Phase 6 backend API; contains
no ML, SHAP, or explanation-generation logic of its own — the explanation
paragraph and recommendation text are rendered exactly as the backend returns
them (see `services/api.ts` and `pages/ResultsPage.tsx`).

## Running the full stack locally

Three things need to be running at once: PostgreSQL, the backend, and this
frontend.

```bash
# 1. Backend (from backend/, with .env already configured — see backend/alembic/README.md)
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Frontend (from frontend/, in a second terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api/*` to `http://127.0.0.1:8000`
(see `vite.config.ts`), so the browser only ever talks to one origin in dev.

**Demo flow**: create an account → sign in → answer the 14 check-in questions
→ submit → see the explanation and recommended next steps. Every step calls
the real backend; nothing in this app is mocked.

## Scripts

| Command | Does |
|---|---|
| `npm run dev` | Start the dev server with the `/api` proxy |
| `npm run build` | Type-check (`tsc -b`) then production build |
| `npm run test` | Run the Vitest suite (feature-schema contract tests) |
| `npm run preview` | Serve the production build locally |

## Auth token storage — a deliberate choice, not an oversight

The access token returned by `POST /auth/login` is held in React state only
(`services/auth.tsx`), for the lifetime of the browser tab. It is **not**
written to `localStorage` or `sessionStorage`.

**Why**: both storage APIs are readable by any JavaScript running on the
origin, so a single XSS vulnerability anywhere in the app or its dependency
tree would hand an attacker a usable token for a student's wellbeing data.
In-memory storage doesn't stop XSS, but it removes the trivial persistent
read — there's nothing sitting in storage to steal, and the token is gone the
moment the tab closes.

**What this costs**: refreshing the page signs the user out. Accepted as a
reasonable trade for a short, single-session assessment flow.

**What would be stronger**: an httpOnly cookie issued by the backend, which
JavaScript cannot read at all. That requires the backend to issue
`Set-Cookie` and add CSRF protection (cookies ride along on cross-site
requests automatically, unlike a bearer token). The Phase 6 API returns the
token in the JSON response body, and changing that contract was out of scope
for this session — recorded here as the concrete next hardening step, not
silently deferred.

## Feature contract

`services/featureSchema.ts` mirrors
`ml_pipeline/artifacts/feature_schema.json` (model v2) exactly: 14 fields, in
schema order, with matching min/max bounds. `services/featureSchema.test.ts`
pins those values against a copy of the schema, so a future retrain that
changes the feature set fails this test rather than silently breaking
predictions. If the model is retrained, update both the schema file and the
test's `SCHEMA_ORDER`/`SCHEMA_BOUNDS` together.
