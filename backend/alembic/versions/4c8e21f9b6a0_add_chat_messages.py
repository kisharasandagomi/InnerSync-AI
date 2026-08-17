"""add chat_messages table (Module 3 chatbot)

Revision ID: 4c8e21f9b6a0
Revises: 9b4f2d7c1a06
Create Date: 2026-08-17 12:05:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '4c8e21f9b6a0'
down_revision: Union[str, None] = '9b4f2d7c1a06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('fallback_reason', sa.String(length=32), nullable=True),
        sa.CheckConstraint("role in ('user','assistant')", name='ck_chat_messages_role'),
    )
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])
    op.create_index('ix_chat_messages_created_at', 'chat_messages', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_chat_messages_created_at', table_name='chat_messages')
    op.drop_index('ix_chat_messages_user_id', table_name='chat_messages')
    op.drop_table('chat_messages')
