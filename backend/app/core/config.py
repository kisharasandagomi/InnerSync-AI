"""Application settings, loaded from environment / .env.

Per `IMPLEMENTATION_RULES.md`: config values (API keys, DB URLs, model paths)
come from `.env` and are never hardcoded or committed. `.env.example` documents
the required variables without carrying real values.

Implemented with `python-dotenv` + `os.environ` rather than `pydantic-settings`
to avoid adding a dependency that is not already in the `mainks` environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# backend/app/core/config.py -> core -> app -> backend -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = REPO_ROOT / "backend" / ".env"

_PLACEHOLDER_SECRETS = {"changeme", "secret", "please-change-me", "your-secret-key", ""}


class ConfigError(RuntimeError):
    """Raised when required configuration is absent or unsafe."""


@dataclass(frozen=True)
class Settings:
    """Runtime configuration.

    Attributes:
        database_url: SQLAlchemy connection URL.
        jwt_secret_key: Token signing key. No default — the app refuses to start
            without it rather than falling back to a guessable value.
        jwt_algorithm: JWT signing algorithm.
        access_token_expire_minutes: Access-token lifetime.
        artifacts_dir: Where the Research World writes versioned artifacts.
        model_filename: Version-stamped model artifact to load.
    """

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    artifacts_dir: Path
    model_filename: str


def _require(name: str) -> str:
    """Read a required environment variable.

    Args:
        name: Variable name.

    Returns:
        Its value.

    Raises:
        ConfigError: If unset or empty.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"{name} is not set. Copy backend/.env.example to backend/.env and fill it in."
        )
    return value


@lru_cache
def get_settings() -> Settings:
    """Load and validate settings once per process.

    Returns:
        The application settings.

    Raises:
        ConfigError: If a required value is missing, or the JWT secret is a
            known placeholder or too short to be safe.
    """
    load_dotenv(ENV_PATH, override=False)

    secret = _require("JWT_SECRET_KEY")
    if secret.lower() in _PLACEHOLDER_SECRETS:
        raise ConfigError("JWT_SECRET_KEY is a placeholder; set a real value in backend/.env")
    if len(secret) < 16:
        raise ConfigError("JWT_SECRET_KEY must be at least 16 characters")

    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "").strip()
    return Settings(
        database_url=_require("DATABASE_URL"),
        jwt_secret_key=secret,
        jwt_algorithm=os.environ.get("JWT_ALGORITHM", "HS256").strip() or "HS256",
        access_token_expire_minutes=int(
            os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60").strip() or 60
        ),
        artifacts_dir=Path(artifacts_dir) if artifacts_dir
        else REPO_ROOT / "ml_pipeline" / "artifacts",
        model_filename=os.environ.get("MODEL_FILENAME", "stress_model_v2.pkl").strip()
        or "stress_model_v2.pkl",
    )
