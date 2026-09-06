"""Add PostgreSQL GIN index for full-text lexical search on document_chunks

Revision ID: 005_phase8_lexical_search_index
Revises: 004_phase7_tutor_study_mode
Create Date: 2026-09-05 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '005_phase8_lexical_search_index'
down_revision: Union[str, None] = '004_phase7_tutor_study_mode'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_document_chunks_content_fts "
            "ON document_chunks USING gin(to_tsvector('english', content))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_document_chunks_content_fts")
