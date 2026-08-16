"""InnerSync AI backend (Production World).

Per ADR-001 this service loads artifacts and pure functions from the Research
World but never trains: `app.ml.predictor` and `app.services` import from
`ml_pipeline.src.*` rather than duplicating explanation or recommendation logic.

`ml_pipeline` lives at the repository root, one level above `backend/`, and is
not an installed distribution. The repo root is therefore added to `sys.path`
here — at package import, before any submodule runs — so the import resolves
however the app is launched (uvicorn from `backend/`, pytest, or Alembic), not
only when the caller happens to have set PYTHONPATH.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
