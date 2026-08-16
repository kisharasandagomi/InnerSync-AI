"""ORM models. Imported here so Alembic autogenerate sees every table."""

from app.models.assessment import Assessment
from app.models.explanation_record import ExplanationRecord
from app.models.recommendation import Recommendation
from app.models.user import User
from app.models.user_profile import UserProfile

__all__ = ["Assessment", "ExplanationRecord", "Recommendation", "User", "UserProfile"]
