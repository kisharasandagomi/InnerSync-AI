"""Registration, login, and account deactivation routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    generate_otp_code,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models.otp_code import OtpCode
from app.models.password_reset_token import PasswordResetToken
from app.services.email import (
    EmailConfigError,
    EmailSendError,
    send_otp_email,
    send_password_reset_email,
)
from app.database.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.auth import (
    ChangePasswordRequest,
    DeactivateAccountRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginResponse,
    MeResponse,
    ResetPasswordRequest,
    TokenResponse,
    UpdateOtpSettingRequest,
    UpdateProfileRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    VerifyOtpRequest,
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


# Login OTP: short-lived, single-use -- long enough to reach the inbox,
# short enough to bound exposure if the email is somehow intercepted. Same
# reasoning as RESET_TOKEN_LIFETIME_MINUTES below, just a tighter window
# appropriate to a code typed back immediately rather than a clicked link.
LOGIN_OTP_LIFETIME_MINUTES = 10

# A 6-digit code has 1,000,000 possibilities -- guessable within the
# 10-minute window if attempts were unbounded. Capping wrong guesses at 5
# per issued code, then requiring a fresh sign-in (a fresh code), keeps the
# effective search space per code at 5 rather than 1,000,000.
MAX_OTP_ATTEMPTS = 5


@router.post("/login", response_model=LoginResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Exchange credentials for an access token, or a request for a one-time code.

    Args:
        payload: Email and password.
        db: Database session.

    Returns:
        `LoginResponse` with `access_token` set directly, for the large
        majority of accounts that have not opted into OTP (round 7); or,
        for an OTP-enabled account, `otp_required=True` and a `login_token`
        to present to `/auth/login/verify-otp` alongside the code just
        emailed to the account. Fails open toward the *existing* behaviour
        on any OTP-send problem -- see the inline comment below -- rather
        than locking a student out of their own account because Resend is
        briefly unavailable.

    Raises:
        HTTPException: 401 if the email is unknown or the password is wrong.
            The same message is used for both so the response does not reveal
            whether an email is registered.
    """
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    # A deactivated account fails the same way as a wrong password, not a
    # distinct "this account is deactivated" message -- revealing that would
    # confirm the email is registered, the same account-enumeration concern
    # this endpoint already avoids for unknown emails and wrong passwords.
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.otp_enabled:
        return LoginResponse(
            access_token=create_access_token(subject=str(user.id)),
            display_name=user.display_name,
        )

    # OTP-enabled: the password alone is correct but not sufficient. Issue a
    # code and a login_token identifying this pending login, the same
    # single-use-hash-only pattern as PasswordResetToken.
    raw_login_token = generate_reset_token()
    code = generate_otp_code()
    now = datetime.now(timezone.utc)
    db.add(
        OtpCode(
            user_id=user.id,
            login_token_hash=hash_reset_token(raw_login_token),
            code_hash=hash_reset_token(code),
            created_at=now,
            expires_at=now + timedelta(minutes=LOGIN_OTP_LIFETIME_MINUTES),
        )
    )
    db.commit()

    try:
        send_otp_email(user.email, code)
    except (EmailConfigError, EmailSendError) as exc:
        # A student who opted into OTP must not be locked out of their own
        # account because Resend is misconfigured or briefly unavailable --
        # that would turn a security feature into an outage. Surface this
        # loudly as a 503 (a deployment/operational problem, matching
        # forgot_password's treatment of the same failure mode) rather than
        # silently falling back to password-only, which would make OTP
        # appear enabled while providing no actual second factor.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not send your sign-in code. {exc}",
        ) from exc

    return LoginResponse(otp_required=True, login_token=raw_login_token)


@router.post("/login/verify-otp", response_model=TokenResponse)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Complete an OTP-gated login given the emailed code.

    Args:
        payload: The `login_token` from `LoginResponse` plus the code.
        db: Database session.

    Returns:
        A signed access token, exactly as a non-OTP login would return.

    Raises:
        HTTPException: 400 if the login_token is unknown, already used,
            expired, or has hit its attempt cap, or the code does not
            match. One message covers all cases so a caller cannot
            distinguish which -- the same discipline `reset_password`
            already applies to its own token, and important here
            specifically so a wrong code cannot be distinguished from an
            expired or exhausted session by trial and error.
    """
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="That code is invalid or has expired. Please sign in again.",
    )

    otp_row = (
        db.query(OtpCode)
        .filter(OtpCode.login_token_hash == hash_reset_token(payload.login_token))
        .one_or_none()
    )
    if otp_row is None or otp_row.used_at is not None:
        raise invalid

    if otp_row.attempts >= MAX_OTP_ATTEMPTS:
        raise invalid

    now = datetime.now(timezone.utc)
    expires_at = otp_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise invalid

    if otp_row.code_hash != hash_reset_token(payload.code):
        # Count the wrong guess against this row's cap, and invalidate the
        # row outright once the cap is reached -- rather than only rejecting
        # once attempts already equals the cap on some later request -- so a
        # student who exhausts their attempts must request a brand new code
        # rather than being left able to notice the boundary and probe it.
        otp_row.attempts += 1
        if otp_row.attempts >= MAX_OTP_ATTEMPTS:
            otp_row.used_at = now
        db.commit()
        raise invalid

    user = db.get(User, otp_row.user_id)
    if user is None or not user.is_active:
        raise invalid

    otp_row.used_at = now
    db.commit()

    return TokenResponse(
        access_token=create_access_token(subject=str(user.id)),
        display_name=user.display_name,
    )


@router.post("/deactivate", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_account(
    payload: DeactivateAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Deactivate the caller's own account.

    Soft-delete only: sets `is_active=False` and records `deactivated_at`.
    Never deletes the row or any associated data -- see
    `docs/governance/data_management_plan.md`'s retention section. The
    caller's data (assessments, chat messages) is left exactly as it was;
    only future authentication is blocked (`login` and `get_current_user`
    both check `is_active`).

    Args:
        payload: Must include the account's current password.
        current_user: The authenticated caller, resolved from their bearer
            token.
        db: Database session.

    Returns:
        Nothing (204).

    Raises:
        HTTPException: 401 if the supplied password does not match.
    """
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )
    current_user.is_active = False
    current_user.deactivated_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the caller's own current profile (round 7).

    Args:
        current_user: The authenticated caller.

    Returns:
        Their id, email, current display name, and OTP setting -- fresh
        from the database, not a snapshot from login. Powers Settings'
        edit-profile and two-factor sections on mount.
    """
    return current_user


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Update the caller's own display name (round 7).

    Args:
        payload: The new display name, or `None`/blank to clear it.
        current_user: The authenticated caller.
        db: Database session.

    Returns:
        The updated user.
    """
    display_name = payload.display_name.strip() if payload.display_name else None
    current_user.display_name = display_name or None
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Change the caller's own password while signed in (round 7).

    Distinct from the forgot/reset-password flow: this requires knowing the
    *current* password, standard practice for an in-session credential
    change -- see `ChangePasswordRequest`'s docstring.

    Args:
        payload: The current password (for confirmation) and the new one.
        current_user: The authenticated caller.
        db: Database session.

    Returns:
        Nothing (204).

    Raises:
        HTTPException: 401 if `current_password` does not match.
    """
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password",
        )
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()


@router.patch("/otp-setting", response_model=MeResponse)
def update_otp_setting(
    payload: UpdateOtpSettingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Turn email one-time-code sign-in on or off for the caller's own account.

    Args:
        payload: The desired setting.
        current_user: The authenticated caller.
        db: Database session.

    Returns:
        The caller's current profile, reflecting the new setting.
    """
    current_user.otp_enabled = payload.enabled
    db.commit()
    db.refresh(current_user)
    return current_user


# Single-use, expires in under an hour -- long enough for a student to reach
# their email, short enough to bound the exposure of a stolen link.
RESET_TOKEN_LIFETIME_MINUTES = 45


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> ForgotPasswordResponse:
    """Request a password reset link.

    Always returns the same message, whether or not `payload.email` belongs
    to a registered account -- see `ForgotPasswordResponse`'s docstring. The
    Resend configuration check happens before the account lookup, so a
    missing `RESEND_API_KEY` fails identically (loudly, as a 503) for every
    request rather than only for requests that would have found a match,
    which would itself be a timing/behaviour leak.

    Args:
        payload: The email to send a reset link to, if registered.
        db: Database session.

    Returns:
        The same generic confirmation message in every case.

    Raises:
        HTTPException: 503 if Resend is not configured. This is a deployment
            problem, not a per-request one -- see `app.services.email`.
    """
    try:
        settings = get_settings()
        if not settings.resend_api_key.strip():
            raise EmailConfigError("RESEND_API_KEY is not set")
    except EmailConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Password reset email is not configured on this server. "
                f"{exc}"
            ),
        ) from exc

    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is not None and user.is_active:
        raw_token = generate_reset_token()
        now = datetime.now(timezone.utc)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_reset_token(raw_token),
                created_at=now,
                expires_at=now + timedelta(minutes=RESET_TOKEN_LIFETIME_MINUTES),
            )
        )
        db.commit()

        reset_link = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
        try:
            send_password_reset_email(user.email, reset_link)
        except EmailSendError:
            # A genuine send failure (Resend outage, bad recipient, etc.) is
            # a server-side problem to investigate, not something to expose
            # to the caller -- doing so would also re-introduce the
            # enumeration signal this endpoint otherwise avoids.
            pass

    return ForgotPasswordResponse()


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    """Set a new password given a valid, unused, unexpired reset token.

    Args:
        payload: The raw token from the emailed link, plus the new password.
        db: Database session.

    Returns:
        Nothing (204).

    Raises:
        HTTPException: 400 if the token is unknown, already used, or expired.
            One message covers all three so a caller cannot distinguish
            "wrong token" from "right token, already used" from "right
            token, expired".
    """
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="This reset link is invalid or has expired. Please request a new one.",
    )

    token_row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_reset_token(payload.token))
        .one_or_none()
    )
    if token_row is None or token_row.used_at is not None:
        raise invalid

    now = datetime.now(timezone.utc)
    expires_at = token_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise invalid

    user = db.get(User, token_row.user_id)
    if user is None or not user.is_active:
        raise invalid

    user.hashed_password = hash_password(payload.new_password)
    token_row.used_at = now

    # Also retire any other outstanding tokens for this user: a successful
    # reset should invalidate every other in-flight reset link, not just the
    # one that was used.
    other_tokens = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != token_row.id,
            PasswordResetToken.used_at.is_(None),
        )
        .all()
    )
    for other in other_tokens:
        other.used_at = now

    db.commit()
