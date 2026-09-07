"""Add workspaces and workspace_documents tables for Phase 12 Multi-Document Intelligence

Revision ID: 010_phase12_workspaces
Revises: 009_phase11_agent_runs
Create Date: 2026-09-07 19:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '010_phase12_workspaces'
down_revision: Union[str, None] = '009_phase11_agent_runs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workspaces',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_workspaces_user_id', 'workspaces', ['user_id'])

    op.create_table(
        'workspace_documents',
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_ws_docs_workspace', 'workspace_documents', ['workspace_id'])
    op.create_index('idx_ws_docs_document', 'workspace_documents', ['document_id'])


def downgrade() -> None:
    op.drop_index('idx_ws_docs_document', table_name='workspace_documents')
    op.drop_index('idx_ws_docs_workspace', table_name='workspace_documents')
    op.drop_table('workspace_documents')
    op.drop_index('idx_workspaces_user_id', table_name='workspaces')
    op.drop_table('workspaces')
