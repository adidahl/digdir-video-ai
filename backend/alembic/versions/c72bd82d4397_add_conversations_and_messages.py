"""add_conversations_and_messages

Revision ID: c72bd82d4397
Revises: c046f6d80ebe
Create Date: 2025-12-05 20:12:09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = 'c72bd82d4397'
down_revision = 'c046f6d80ebe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )
    
    # Create indexes for conversations
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_organization_id', 'conversations', ['organization_id'])
    op.create_index('ix_conversations_created_at', 'conversations', ['created_at'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),  # 'user' or 'assistant'
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('sources', JSONB, nullable=True),  # [{video_id, title, timestamp, text}]
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for messages
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])


def downgrade() -> None:
    # Drop messages table first (foreign key dependency)
    op.drop_index('ix_messages_created_at', 'messages')
    op.drop_index('ix_messages_conversation_id', 'messages')
    op.drop_table('messages')
    
    # Drop conversations table
    op.drop_index('ix_conversations_created_at', 'conversations')
    op.drop_index('ix_conversations_organization_id', 'conversations')
    op.drop_index('ix_conversations_user_id', 'conversations')
    op.drop_table('conversations')
