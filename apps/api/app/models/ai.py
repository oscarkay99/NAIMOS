import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, now_utc, uuid_pk
from app.models.enums import AIReviewStatus, DetectionType, RiskCategory


class AIDetection(Base, TimestampMixin):
    """An AI-flagged environmental change signal. Always requires human
    verification before it can back any operational claim (section 7)."""

    __tablename__ = "ai_detections"

    id: Mapped[uuid.UUID] = uuid_pk()
    location: Mapped[str] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    detection_type: Mapped[DetectionType] = mapped_column(Enum(DetectionType, name="detection_type"))
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 - 1.0
    estimated_area_hectares: Mapped[float | None] = mapped_column(Float, nullable=True)

    observation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_observation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped[str] = mapped_column(String(64), default="mock_change_detection")
    requires_verification: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    review_status: Mapped[AIReviewStatus] = mapped_column(
        Enum(AIReviewStatus, name="ai_review_status"), default=AIReviewStatus.PENDING
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)

    model_name: Mapped[str] = mapped_column(String(64), default="mock-change-detector")
    model_version: Mapped[str] = mapped_column(String(32), default="0.1.0-demo")


class RiskScore(Base, TimestampMixin):
    """Operational Risk / Investigation Priority Score for a location - NOT a
    certainty that illegal mining is occurring (section 3)."""

    __tablename__ = "risk_scores"

    id: Mapped[uuid.UUID] = uuid_pk()
    incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id"), nullable=True, index=True)
    location: Mapped[str] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    category: Mapped[RiskCategory] = mapped_column(Enum(RiskCategory, name="risk_category"))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), default="risk-engine-0.1.0")
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    factors: Mapped[list["RiskFactor"]] = relationship(back_populates="risk_score", cascade="all, delete-orphan")


class RiskFactor(Base):
    __tablename__ = "risk_factors"

    id: Mapped[uuid.UUID] = uuid_pk()
    risk_score_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_scores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. "recent field reports"
    points: Mapped[int] = mapped_column(Integer, nullable=False)  # contribution, e.g. +25
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)

    risk_score: Mapped["RiskScore"] = relationship(back_populates="factors")


class AIQuery(Base):
    """Audit trail for every natural-language query sent to the AI assistant
    (section 20/35) - required for auditability of AI-mediated data access."""

    __tablename__ = "ai_queries"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    detected_intent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    generated_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str] = mapped_column(String(64), default="mock-llm")
    model_version: Mapped[str] = mapped_column(String(32), default="0.1.0-demo")
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
