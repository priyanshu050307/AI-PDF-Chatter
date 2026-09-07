import uuid
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Uuid, JSON, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    run_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dataset_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pipeline_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    llm_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    embedding_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    embedding_dimension: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reranker_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    vision_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    pipeline_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="COMPLETED")
    
    recall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precision_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    faithfulness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    metrics_summary: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    quality_gates_result: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    latency_summary: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    reliability_summary: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    case_results: Mapped[List["EvalCaseResult"]] = relationship("EvalCaseResult", back_populates="run", cascade="all, delete-orphan")


class EvalCaseResult(Base):
    __tablename__ = "eval_case_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False)
    case_id: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_evidence: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    retrieved_evidence: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    generated_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citations: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    human_review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="UNREVIEWED")
    human_review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    run: Mapped["EvalRun"] = relationship("EvalRun", back_populates="case_results")
    human_reviews: Mapped[List["EvalHumanReview"]] = relationship("EvalHumanReview", back_populates="case_result", cascade="all, delete-orphan")


class EvalHumanReview(Base):
    __tablename__ = "eval_human_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_result_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("eval_case_results.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    case_result: Mapped["EvalCaseResult"] = relationship("EvalCaseResult", back_populates="human_reviews")
