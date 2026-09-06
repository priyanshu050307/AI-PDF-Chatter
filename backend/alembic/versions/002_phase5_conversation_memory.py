"""phase5_conversation_memory

Revision ID: 002_phase5_conversation_memory
Revises: 001_initial_schema
Create Date: 2026-09-04 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_phase5_conversation_memory'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add summary columns to conversations
    op.add_column('conversations', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('conversations', sa.Column('summary_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversations', sa.Column('summary_message_count', sa.Integer(), server_default='0', nullable=False))

    # Add indexes
    op.create_index('idx_conversations_user_doc', 'conversations', ['user_id', 'document_id', 'updated_at'], unique=False)
    op.create_index('idx_chat_messages_conv_created', 'chat_messages', ['conversation_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_chat_messages_conv_created', table_name='chat_messages')
    op.drop_index('idx_conversations_user_doc', table_name='conversations')
    op.drop_column('conversations', 'summary_message_count')
    op.drop_column('conversations', 'summary_updated_at')
    op.drop_column('conversations', 'summary')
