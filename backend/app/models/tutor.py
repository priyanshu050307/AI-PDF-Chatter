import uuid
import enum
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import String, Text, Enum as SQLEnum, ForeignKey, DateTime, Uuid, JSON, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class TutorStatus(str, enum.Enum):
    CREATED = "CREATED"
    ASSESSING = "ASSESSING"
    TEACHING = "TEACHING"
    QUESTION = "QUESTION"
    EVALUATING = "EVALUATING"
    FEEDBACK = "FEEDBACK"
    NEXT_CONCEPT = "NEXT_CONCEPT"
    COMPLETED = "COMPLETED"


class TutorDifficulty(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class FlashcardRating(str, enum.Enum):
    AGAIN = "AGAIN"
    HARD = "HARD"
    GOOD = "GOOD"
    EASY = "EASY"


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    topic_scope: Mapped[dict] = mapped_column(JSON, default=dict)
    difficulty: Mapped[TutorDifficulty] = mapped_column(SQLEnum(TutorDifficulty), default=TutorDifficulty.INTERMEDIATE, nullable=False)
    learning_goal: Mapped[str] = mapped_column(String(50), default="UNDERSTAND", nullable=False)
    status: Mapped[TutorStatus] = mapped_column(SQLEnum(TutorStatus), default=TutorStatus.CREATED, nullable=False)
    current_concept: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mastery_state: Mapped[dict] = mapped_column(JSON, default=dict)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    history: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    document = relationship("Document")
    flashcards = relationship("StudyFlashcard", back_populates="session", cascade="all, delete-orphan")
    quizzes = relationship("StudyQuiz", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_study_sessions_user_doc", "user_id", "document_id", "updated_at"),
    )


class StudyFlashcard(Base):
    __tablename__ = "study_flashcards"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    source_citations: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[TutorDifficulty] = mapped_column(SQLEnum(TutorDifficulty), default=TutorDifficulty.INTERMEDIATE, nullable=False)
    review_rating: Mapped[Optional[FlashcardRating]] = mapped_column(SQLEnum(FlashcardRating), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("StudySession", back_populates="flashcards")


class StudyQuiz(Base):
    __tablename__ = "study_quizzes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    topic_scope: Mapped[dict] = mapped_column(JSON, default=dict)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    user_answers: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluation_results: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("StudySession", back_populates="quizzes")
