"""Add agent_runs and agent_steps tables

Revision ID: 009_phase11_agent_runs
Revises: 008_phase10_narrative_intelligence
Create Date: 2026-09-07 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '009_phase11_agent_runs'
down_revision: Union[str, None] = '008_phase10_narrative_intelligence'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', sa.Uuid(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='CREATED'),
        sa.Column('route', sa.String(length=50), nullable=False, server_default='AGENTIC_RAG'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('step_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_steps', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('provider', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('telemetry_json', sa.JSON(), nullable=True),
    )
    op.create_index('idx_agent_runs_user_doc', 'agent_runs', ['user_id', 'document_id'])

    op.create_table(
        'agent_steps',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('run_id', sa.Uuid(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),  # PLAN, TOOL_CALL, SYNTHESIS
        sa.Column('tool_name', sa.String(length=100), nullable=True),
        sa.Column('tool_input_json', sa.JSON(), nullable=True),
        sa.Column('tool_output_json', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='COMPLETED'),  # COMPLETED, FAILED, TIMED_OUT
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('evidence_ids_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_agent_steps_run_step', 'agent_steps', ['run_id', 'step_index'])


def downgrade() -> None:
    op.drop_index('idx_agent_steps_run_step', table_name='agent_steps')
    op.drop_table('agent_steps')
    op.drop_index('idx_agent_runs_user_doc', table_name='agent_runs')
    op.drop_table('agent_runs')
