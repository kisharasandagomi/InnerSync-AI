# Software Engineering Skill

Trigger: any code written in `backend/`, `frontend/`, or `ml_pipeline/src/`.

Follow Clean Architecture, SOLID, modular design, separation of concerns, and
prefer maintainable production-quality code over quick hacks — even in a
dissertation project, examiners can and do read the code.

Concretely:
- Python: PEP8, type hints on every function signature, Google-style
  docstrings (Args/Returns/Raises), specific exception handling (no bare
  `except:`).
- One responsibility per module. If a file is doing preprocessing AND
  training AND evaluation, split it.
- No hardcoded values (paths, API keys, thresholds) — pull from
  `backend/app/core/config.py` / `.env`.
- No duplicate logic between `ml_pipeline/` and `backend/app/` — the backend
  loads artifacts, it does not reimplement preprocessing or training logic.
- Every new module needs: a one-line purpose docstring at the top of the
  file, and a test where practical (see the testing skill).

Prefer explicit, readable code over clever one-liners — this codebase will be
read by a supervisor and examiner, not just run.
