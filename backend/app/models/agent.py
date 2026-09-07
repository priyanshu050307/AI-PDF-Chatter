import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON, Index, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class AgentRun(Base):
    """ORM Model representing a single Agentic Reasoning Run session."""
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)

    query = Column(Text, nullable=False)
    state = Column(String(50), nullable=False, default="CREATED")  # CREATED, ROUTING, PLANNING, EXECUTING, OBSERVING, SYNTHESIZING, COMPLETED, FAILED, TIMED_OUT
    route = Column(String(50), nullable=False, default="AGENTIC_RAG")  # SIMPLE_FACTUAL, AGENTIC_RAG, CHARACTER_NARRATIVE, COMPARISON, ANNOTATION_ANALYSIS

    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    step_count = Column(Integer, nullable=False, default=0)
    max_steps = Column(Integer, nullable=False, default=5)
    latency_ms = Column(Float, nullable=True)

    model = Column(String(100), nullable=True)
    provider = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    telemetry_json = Column(JSON, nullable=True)

    # Relationships
    steps = relationship("AgentStep", back_populates="run", cascade="all, delete-orphan", order_by="AgentStep.step_index.asc()")

    __table_args__ = (
        Index("idx_agent_runs_user_doc", "user_id", "document_id"),
    )


class AgentStep(Base):
    """ORM Model representing an individual step / tool invocation within an Agent Run."""
    __tablename__ = "agent_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    step_index = Column(Integer, nullable=False)

    action_type = Column(String(50), nullable=False)  # PLAN, TOOL_CALL, SYNTHESIS
    tool_name = Column(String(100), nullable=True)
    tool_input_json = Column(JSON, nullable=True)
    tool_output_json = Column(JSON, nullable=True)

    status = Column(String(50), nullable=False, default="COMPLETED")  # COMPLETED, FAILED, TIMED_OUT
    duration_ms = Column(Float, nullable=True)
    evidence_ids_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    run = relationship("AgentRun", back_populates="steps")

    __table_args__ = (
        Index("idx_agent_steps_run_step", "run_id", "step_index"),
    )
