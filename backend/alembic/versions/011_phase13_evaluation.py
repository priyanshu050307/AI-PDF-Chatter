"""Add Phase 13 Unified Evaluation schema extensions

Revision ID: 011_phase13_evaluation
Revises: 010_phase12_workspaces
Create Date: 2026-09-07 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '011_phase13_evaluation'
down_revision: Union[str, None] = '010_phase12_workspaces'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = {col['name'] for col in inspector.get_columns('eval_runs')}

    cols_to_add = [
        ('user_id', sa.Uuid(as_uuid=True)),
        ('dataset_name', sa.String(length=100)),
        ('dataset_version', sa.String(length=100)),
        ('pipeline_version', sa.String(length=100)),
        ('prompt_version', sa.String(length=100)),
        ('llm_provider', sa.String(length=100)),
        ('llm_model', sa.String(length=100)),
        ('embedding_provider', sa.String(length=100)),
        ('embedding_model', sa.String(length=100)),
        ('embedding_dimension', sa.Integer()),
        ('reranker_provider', sa.String(length=100)),
        ('vision_provider', sa.String(length=100)),
        ('status', sa.String(length=50)),
        ('metrics_summary', sa.JSON()),
        ('quality_gates_result', sa.JSON()),
        ('latency_summary', sa.JSON()),
        ('reliability_summary', sa.JSON()),
        ('completed_at', sa.DateTime(timezone=True)),
        ('metadata_json', sa.JSON()),
    ]

    for col_name, col_type in cols_to_add:
        if col_name not in existing_cols:
            op.add_column('eval_runs', sa.Column(col_name, col_type, nullable=True))

    existing_tables = inspector.get_table_names()

    # 2. Create eval_case_results table
    if 'eval_case_results' not in existing_tables:
        op.create_table(
            'eval_case_results',
            sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
            sa.Column('run_id', sa.Uuid(as_uuid=True), sa.ForeignKey('eval_runs.id', ondelete='CASCADE'), nullable=False),
            sa.Column('case_id', sa.String(length=100), nullable=False),
            sa.Column('category', sa.String(length=100), nullable=True),
            sa.Column('difficulty', sa.String(length=50), nullable=True),
            sa.Column('question', sa.Text(), nullable=False),
            sa.Column('expected_evidence', sa.JSON(), nullable=True, server_default='[]'),
            sa.Column('retrieved_evidence', sa.JSON(), nullable=True, server_default='[]'),
            sa.Column('generated_answer', sa.Text(), nullable=True),
            sa.Column('citations', sa.JSON(), nullable=True, server_default='[]'),
            sa.Column('metrics', sa.JSON(), nullable=True, server_default='{}'),
            sa.Column('passed', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('failure_reason', sa.Text(), nullable=True),
            sa.Column('human_review_status', sa.String(length=50), nullable=False, server_default='UNREVIEWED'),
            sa.Column('human_review_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )
        op.create_index('idx_eval_cases_run_id', 'eval_case_results', ['run_id'])
        op.create_index('idx_eval_cases_case_id', 'eval_case_results', ['case_id'])

    # 3. Create eval_human_reviews table
    if 'eval_human_reviews' not in existing_tables:
        op.create_table(
            'eval_human_reviews',
            sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
            sa.Column('case_result_id', sa.Uuid(as_uuid=True), sa.ForeignKey('eval_case_results.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('label', sa.String(length=50), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )
        op.create_index('idx_eval_reviews_case_res', 'eval_human_reviews', ['case_result_id'])
        op.create_index('idx_eval_reviews_user_id', 'eval_human_reviews', ['user_id'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'eval_human_reviews' in existing_tables:
        op.drop_index('idx_eval_reviews_user_id', table_name='eval_human_reviews')
        op.drop_index('idx_eval_reviews_case_res', table_name='eval_human_reviews')
        op.drop_table('eval_human_reviews')

    if 'eval_case_results' in existing_tables:
        op.drop_index('idx_eval_cases_case_id', table_name='eval_case_results')
        op.drop_index('idx_eval_cases_run_id', table_name='eval_case_results')
        op.drop_table('eval_case_results')
