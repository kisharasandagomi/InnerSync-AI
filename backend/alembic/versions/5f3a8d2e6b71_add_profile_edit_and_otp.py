"""add profile edit support and email OTP login (round 7)

Revision ID: 5f3a8d2e6b71
Revises: 2a9c7e4f1b03
Create Date: 2026-08-21 09:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '5f3a8d2e6b71'
down_revision: Union[str, None] = '2a9c7e4f1b03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Opt-in, default False so existing accounts are not disrupted -- see
    # app.models.user.User.otp_enabled's docstring.
    op.add_column(
        'users',
        sa.Column('otp_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        'otp_codes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        # SHA-256 hex digests of the login_token and the 6-digit code --
        # never the raw values, mirroring password_reset_tokens.token_hash.
        sa.Column('login_token_hash', sa.String(length=64), nullable=False, unique=True),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_otp_codes_login_token_hash', 'otp_codes', ['login_token_hash'])
    op.create_index('ix_otp_codes_user_id', 'otp_codes', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_otp_codes_user_id', table_name='otp_codes')
    op.drop_index('ix_otp_codes_login_token_hash', table_name='otp_codes')
    op.drop_table('otp_codes')
    op.drop_column('users', 'otp_enabled')
