"""Add document_elements table for Phase 9 Multimodal PDF Intelligence

Revision ID: 007_phase9_multimodal_elements
Revises: 006_real_ai_embedding_dimension
Create Date: 2026-09-07 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '007_phase9_multimodal_elements'
down_revision: Union[str, None] = '006_real_ai_embedding_dimension'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_elements',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('element_type', sa.String(length=64), nullable=False),
        sa.Column('bbox_json', sa.JSON(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('structured_data', sa.JSON(), nullable=True),
        sa.Column('image_storage_key', sa.String(length=1024), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_document_elements_doc_page', 'document_elements', ['document_id', 'page_number'])
    op.create_index('idx_document_elements_doc_type', 'document_elements', ['document_id', 'element_type'])


def downgrade() -> None:
    op.drop_index('idx_document_elements_doc_type', table_name='document_elements')
    op.drop_index('idx_document_elements_doc_page', table_name='document_elements')
    op.drop_table('document_elements')
