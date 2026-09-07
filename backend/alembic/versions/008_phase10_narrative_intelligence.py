"""Add narrative_events table and temporal columns to entity_relationships

Revision ID: 008_phase10_narrative_intelligence
Revises: 007_phase9_multimodal_elements
Create Date: 2026-09-07 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '008_phase10_narrative_intelligence'
down_revision: Union[str, None] = '007_phase9_multimodal_elements'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'narrative_events',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('participants_json', sa.JSON(), nullable=True),
        sa.Column('location_name', sa.String(length=255), nullable=True),
        sa.Column('evidence_chunk_id', sa.Uuid(as_uuid=True), sa.ForeignKey('document_chunks.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_narrative_events_doc_page', 'narrative_events', ['document_id', 'page_number'])

    with op.batch_alter_table('entity_relationships') as batch_op:
        batch_op.add_column(sa.Column('observed_page', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('valid_from_page', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('valid_to_page', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('entity_relationships') as batch_op:
        batch_op.drop_column('valid_to_page')
        batch_op.drop_column('valid_from_page')
        batch_op.drop_column('observed_page')

    op.drop_index('idx_narrative_events_doc_page', table_name='narrative_events')
    op.drop_table('narrative_events')
