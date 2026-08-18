"""add password reset tokens (round 4)

Revision ID: 2a9c7e4f1b03
Revises: 1f6a3d8e5c92
Create Date: 2026-08-18 15:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '2a9c7e4f1b03'
down_revision: Union[str, None] = '1f6a3d8e5c92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        # SHA-256 hex digest of the raw token, never the raw token itself --
        # a database read alone must not yield a usable reset link.
        sa.Column('token_hash', sa.String(length=64), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash']
    )
    op.create_index(
        'ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id']
    )


def downgrade() -> None:
    op.drop_index('ix_password_reset_tokens_user_id', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_token_hash', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
