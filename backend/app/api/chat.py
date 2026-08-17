"""Chatbot routes (Module 3): send a message, fetch history.

Read `app/chatbot/service.py`'s module docstring before touching this file —
it states the hard boundary this router must not cross (never predicts
stress, never touches `Assessment`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.chatbot.gemini_client import ChatConfigError
from app.chatbot.service import MAX_HISTORY_MESSAGES, SessionLimitExceeded, send_message
from app.database.session import get_db
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.schemas.chat import ChatMessageIn, ChatMessageOut, ChatTurnResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages", response_model=ChatTurnResponse, status_code=status.HTTP_201_CREATED)
def post_message(
    payload: ChatMessageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatTurnResponse:
    """Send one message and get a reply.

    Args:
        payload: The student's message text.
        db: Database session.
        current_user: Authenticated sender.

    Returns:
        Both persisted rows: the student's message and the reply.

    Raises:
        HTTPException: 429 if the caller has used up this session's turn
            cap (see `app.chatbot.service.MAX_TURNS_PER_SESSION`). 503 if
            `GEMINI_API_KEY` is missing or invalid — a configuration
            problem, told to the caller plainly rather than hidden behind a
            canned reply, per `CLAUDE.md`.
    """
    try:
        result = send_message(db=db, user_id=current_user.id, text=payload.content)
    except SessionLimitExceeded as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except ChatConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return ChatTurnResponse(
        user_message=ChatMessageOut.model_validate(result.user_message),
        assistant_message=ChatMessageOut.model_validate(result.assistant_message),
    )


@router.get("/messages", response_model=list[ChatMessageOut])
def get_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessage]:
    """Return the caller's own recent messages, oldest first.

    Read-only, for the frontend to restore conversation continuity across
    page loads — mirrors `GET /assessments/history`'s shape and intent.

    Args:
        db: Database session.
        current_user: Authenticated caller — history is scoped to their own
            rows only.

    Returns:
        Up to `MAX_HISTORY_MESSAGES` most recent messages, oldest first.
    """
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    rows.reverse()
    return rows
