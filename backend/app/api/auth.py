"""Registration and login routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> User:
    """Create a new account.

    Args:
        payload: Email and password.
        db: Database session.

    Returns:
        The created user, serialised without the password hash.

    Raises:
        HTTPException: 409 if the email is already registered.
    """
    existing = db.query(User).filter(User.email == payload.email).one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    display_name = payload.display_name.strip() if payload.display_name else None
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        display_name=display_name or None,
    )
    db.add(user)
    db.flush()  # assign user.id without committing

    hobby = payload.hobby.strip() if payload.hobby else None
    if hobby:
        db.add(UserProfile(user_id=user.id, hobby=hobby))

    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange credentials for an access token.

    Args:
        payload: Email and password.
        db: Database session.

    Returns:
        A signed access token.

    Raises:
        HTTPException: 401 if the email is unknown or the password is wrong.
            The same message is used for both so the response does not reveal
            whether an email is registered.
    """
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return TokenResponse(
        access_token=create_access_token(subject=str(user.id)),
        display_name=user.display_name,
    )
