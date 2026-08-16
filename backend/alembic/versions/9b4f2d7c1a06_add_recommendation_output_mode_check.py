"""add mutual-exclusivity check constraint on recommendations output mode

Revision ID: 9b4f2d7c1a06
Revises: 3e72333cb8f4
Create Date: 2026-08-17 09:12:41.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = '9b4f2d7c1a06'
down_revision: Union[str, None] = '3e72333cb8f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "ck_recommendations_mutually_exclusive_output_mode"

# `actions` is JSONB on Postgres (see app.models.assessment.JSONType), so the
# array-length function here is `jsonb_array_length`, not the plain-JSON
# `json_array_length` the ORM model uses for SQLite in tests — see the
# comment on `Recommendation.__table_args__` for why the two are allowed to
# differ. Every row written by the application already satisfies this: the
# point-in-time engine, the affirmation path, and the Adaptive Recovery
# Framework each set exactly one of the three modes. This constraint closes
# the gap where a future code change could silently violate that invariant.
CONDITION = (
    "(CASE WHEN is_affirmation THEN 1 ELSE 0 END)"
    " + (CASE WHEN is_escalation THEN 1 ELSE 0 END)"
    " + (CASE WHEN jsonb_array_length(actions) > 0 THEN 1 ELSE 0 END) <= 1"
)


def upgrade() -> None:
    op.create_check_constraint(CONSTRAINT_NAME, "recommendations", CONDITION)


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "recommendations", type_="check")
