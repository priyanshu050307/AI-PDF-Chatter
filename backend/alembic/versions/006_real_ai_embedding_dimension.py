"""Update document_chunks.embedding vector column dimension to 768 for Ollama embeddinggemma

Revision ID: 006_real_ai_embedding_dimension
Revises: 005_phase8_lexical_search_index
Create Date: 2026-09-06 08:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '006_real_ai_embedding_dimension'
down_revision: Union[str, None] = '005_phase8_lexical_search_index'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768) USING NULL;"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536) USING NULL;"
        )
