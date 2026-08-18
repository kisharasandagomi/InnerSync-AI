"""Shared FastAPI dependencies: current user resolution and predictor access."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.session import get_db
from app.ml.predictor import StressPredictor, get_predictor
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a bearer token.

    Args:
        credentials: Parsed Authorization header, if present.
        db: Database session.

    Returns:
        The authenticated user.

    Raises:
        HTTPException: 401 if the token is absent, invalid, expired, or refers
            to a user that no longer exists.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or not credentials.credentials:
        raise unauthorized

    subject = decode_access_token(credentials.credentials)
    if subject is None:
        raise unauthorized

    try:
        user_id = int(subject)
    except ValueError as exc:
        raise unauthorized from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        # A still-unexpired token for a since-deactivated account must not
        # keep working -- see app.api.auth's deactivate endpoint.
        raise unauthorized
    return user


def get_model(predictor: StressPredictor = Depends(get_predictor)) -> StressPredictor:
    """Provide the loaded predictor to routes.

    Args:
        predictor: Cached predictor instance.

    Returns:
        The predictor.
    """
    return predictor
