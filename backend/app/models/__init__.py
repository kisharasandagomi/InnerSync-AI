"""ORM models. Imported here so Alembic autogenerate sees every table."""

from app.models.assessment import Assessment
from app.models.chat_message import ChatMessage
from app.models.explanation_record import ExplanationRecord
from app.models.password_reset_token import PasswordResetToken
from app.models.recommendation import Recommendation
from app.models.user import User
from app.models.user_profile import UserProfile

__all__ = [
    "Assessment",
    "ChatMessage",
    "ExplanationRecord",
    "PasswordResetToken",
    "Recommendation",
    "User",
    "UserProfile",
]
