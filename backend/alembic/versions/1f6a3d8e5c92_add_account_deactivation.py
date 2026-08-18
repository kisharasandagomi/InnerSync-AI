"""add account deactivation fields (round 4)

Revision ID: 1f6a3d8e5c92
Revises: 7a1d9c4e2b83
Create Date: 2026-08-18 14:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '1f6a3d8e5c92'
down_revision: Union[str, None] = '7a1d9c4e2b83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        'users',
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'deactivated_at')
    op.drop_column('users', 'is_active')
