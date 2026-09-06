import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pipeline_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recall_score: Mapped[float] = mapped_column(Float, nullable=True)
    precision_score: Mapped[float] = mapped_column(Float, nullable=True)
    faithfulness_score: Mapped[float] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
