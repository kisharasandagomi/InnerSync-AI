"""add attempts column to otp_codes for a max-tries brute-force cap (round 7)

Revision ID: 1729cae1172b
Revises: 5f3a8d2e6b71
Create Date: 2026-08-21 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '1729cae1172b'
down_revision: Union[str, None] = '5f3a8d2e6b71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Counts wrong-code guesses against one row; verify_otp invalidates the
    # row once this reaches app.api.auth.MAX_OTP_ATTEMPTS, so a 6-digit code
    # cannot be brute-forced across the 10-minute window it's valid for.
    op.add_column(
        'otp_codes',
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('otp_codes', 'attempts')
