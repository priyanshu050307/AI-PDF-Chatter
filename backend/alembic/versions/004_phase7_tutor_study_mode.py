"""Add Phase 7 StudySession, StudyFlashcard, and StudyQuiz tables

Revision ID: 004_phase7_tutor_study_mode
Revises: 003_phase6_highlights_annotations
Create Date: 2026-09-05 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '004_phase7_tutor_study_mode'
down_revision: Union[str, None] = '003_phase6_highlights_annotations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create study_sessions table
    op.create_table(
        'study_sessions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('topic_scope', sa.JSON(), nullable=True),
        sa.Column('difficulty', sa.Enum('BEGINNER', 'INTERMEDIATE', 'ADVANCED', name='tutordifficulty'), nullable=False, server_default='INTERMEDIATE'),
        sa.Column('learning_goal', sa.String(length=50), nullable=False, server_default='UNDERSTAND'),
        sa.Column('status', sa.Enum('CREATED', 'ASSESSING', 'TEACHING', 'QUESTION', 'EVALUATING', 'FEEDBACK', 'NEXT_CONCEPT', 'COMPLETED', name='tutorstatus'), nullable=False, server_default='CREATED'),
        sa.Column('current_concept', sa.String(length=255), nullable=True),
        sa.Column('mastery_state', sa.JSON(), nullable=True),
        sa.Column('progress_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('history', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_study_sessions_user_id', 'study_sessions', ['user_id'], unique=False)
    op.create_index('idx_study_sessions_doc_id', 'study_sessions', ['document_id'], unique=False)
    op.create_index('idx_study_sessions_user_doc', 'study_sessions', ['user_id', 'document_id', 'updated_at'], unique=False)

    # 2. Create study_flashcards table
    op.create_table(
        'study_flashcards',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('study_sessions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('front', sa.Text(), nullable=False),
        sa.Column('back', sa.Text(), nullable=False),
        sa.Column('source_citations', sa.JSON(), nullable=True),
        sa.Column('difficulty', sa.Enum('BEGINNER', 'INTERMEDIATE', 'ADVANCED', name='tutordifficulty', create_type=False), nullable=False, server_default='INTERMEDIATE'),
        sa.Column('review_rating', sa.Enum('AGAIN', 'HARD', 'GOOD', 'EASY', name='flashcardrating'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_study_flashcards_user_id', 'study_flashcards', ['user_id'], unique=False)
    op.create_index('idx_study_flashcards_doc_id', 'study_flashcards', ['document_id'], unique=False)
    op.create_index('idx_study_flashcards_session_id', 'study_flashcards', ['session_id'], unique=False)

    # 3. Create study_quizzes table
    op.create_table(
        'study_quizzes',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('study_sessions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('topic_scope', sa.JSON(), nullable=True),
        sa.Column('questions', sa.JSON(), nullable=True),
        sa.Column('user_answers', sa.JSON(), nullable=True),
        sa.Column('evaluation_results', sa.JSON(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_study_quizzes_user_id', 'study_quizzes', ['user_id'], unique=False)
    op.create_index('idx_study_quizzes_doc_id', 'study_quizzes', ['document_id'], unique=False)
    op.create_index('idx_study_quizzes_session_id', 'study_quizzes', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_study_quizzes_session_id', table_name='study_quizzes')
    op.drop_index('idx_study_quizzes_doc_id', table_name='study_quizzes')
    op.drop_index('idx_study_quizzes_user_id', table_name='study_quizzes')
    op.drop_table('study_quizzes')

    op.drop_index('idx_study_flashcards_session_id', table_name='study_flashcards')
    op.drop_index('idx_study_flashcards_doc_id', table_name='study_flashcards')
    op.drop_index('idx_study_flashcards_user_id', table_name='study_flashcards')
    op.drop_table('study_flashcards')

    op.drop_index('idx_study_sessions_user_doc', table_name='study_sessions')
    op.drop_index('idx_study_sessions_doc_id', table_name='study_sessions')
    op.drop_index('idx_study_sessions_user_id', table_name='study_sessions')
    op.drop_table('study_sessions')
