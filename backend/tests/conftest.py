"""Test fixtures.

Database note: these tests run against an in-memory SQLite database, which is a
substitute for PostgreSQL and is labelled as such rather than presented as
equivalent. It exercises the ORM models, routes, auth, and the full
predict/explain/recommend pipeline, but it does **not** verify the Alembic
migrations or the PostgreSQL-specific JSONB variant. Those require a reachable
Postgres instance — see the session notes on why one was unavailable here.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
for path in (str(BACKEND_DIR), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

# Must be set before app.core.config is imported anywhere.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-for-production-use")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401  (registers tables on Base.metadata)
from app.database.base import Base  # noqa: E402
from app.database.session import get_db  # noqa: E402

# Aliased: a bare `app` would be rebound to the *package* by `import app.models`
# above, shadowing the FastAPI instance.
from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture(name="db_session")
def db_session_fixture() -> Iterator[Session]:
    """Provide an isolated in-memory database for one test."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(name="client")
def client_fixture(db_session: Session) -> Iterator[TestClient]:
    """Provide a TestClient backed by the isolated test database."""

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient) -> dict[str, str]:
    """Register and log in a user, returning bearer auth headers."""
    credentials = {"email": "student@example.ac.uk", "password": "correct-horse-battery"}
    client.post("/auth/register", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
