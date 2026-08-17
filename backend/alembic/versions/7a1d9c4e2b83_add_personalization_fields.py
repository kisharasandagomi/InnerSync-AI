"""add display_name, hobby, and comparative trend audit columns (round 3)

Revision ID: 7a1d9c4e2b83
Revises: 4c8e21f9b6a0
Create Date: 2026-08-18 09:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7a1d9c4e2b83'
down_revision: Union[str, None] = '4c8e21f9b6a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('display_name', sa.String(length=80), nullable=True))
    op.add_column('user_profiles', sa.Column('hobby', sa.String(length=80), nullable=True))
    op.add_column('recommendations', sa.Column('comparative_trend_outcome', sa.Text(), nullable=True))
    op.add_column('recommendations', sa.Column('comparative_trend_message', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('recommendations', 'comparative_trend_message')
    op.drop_column('recommendations', 'comparative_trend_outcome')
    op.drop_column('user_profiles', 'hobby')
    op.drop_column('users', 'display_name')
