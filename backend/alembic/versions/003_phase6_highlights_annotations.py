"""Add Phase 6 highlight bounding_box, chapter_title, section_title and compound index

Revision ID: 003_phase6_highlights_annotations
Revises: 002_phase5_conversation_memory
Create Date: 2026-09-04 20:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003_phase6_highlights_annotations'
down_revision: Union[str, None] = '002_phase5_conversation_memory'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('highlights', sa.Column('bounding_box', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('highlights', sa.Column('chapter_title', sa.String(length=255), nullable=True))
    op.add_column('highlights', sa.Column('section_title', sa.String(length=255), nullable=True))
    op.create_index('idx_highlights_doc_user_page', 'highlights', ['document_id', 'user_id', 'page_number'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_highlights_doc_user_page', table_name='highlights')
    op.drop_column('highlights', 'section_title')
    op.drop_column('highlights', 'chapter_title')
    op.drop_column('highlights', 'bounding_box')
