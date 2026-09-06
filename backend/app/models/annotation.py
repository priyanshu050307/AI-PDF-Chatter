import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, Index, Uuid, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ReadingProgress(Base):
    __tablename__ = "reading_progress"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    current_page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    scroll_position_pct: Mapped[float] = mapped_column(Float, default=0.0)
    last_opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="reading_progresses")
    document = relationship("Document", back_populates="reading_progresses")

    __table_args__ = (
        Index("idx_reading_progress_user_doc", "user_id", "document_id", unique=True),
    )


class Highlight(Base):
    __tablename__ = "highlights"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_text: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String(30), default="yellow")
    note_text: Mapped[str] = mapped_column(Text, nullable=True)
    bounding_box: Mapped[dict] = mapped_column(JSONB().with_variant(JSON, "sqlite"), nullable=True)
    chapter_title: Mapped[str] = mapped_column(String(255), nullable=True)
    section_title: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="highlights")
    document = relationship("Document", back_populates="highlights")

    __table_args__ = (
        Index("idx_highlights_doc_user", "document_id", "user_id"),
        Index("idx_highlights_doc_user_page", "document_id", "user_id", "page_number"),
    )
