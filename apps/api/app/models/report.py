import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, now_utc, uuid_pk


class Report(Base):
    """A generated intelligence report or PRO communication artifact. Content is
    built only from database-backed sources — see report_sources (section 16/17)."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "executive_brief", "press_briefing"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(64), default="mock-llm")
    model_version: Mapped[str] = mapped_column(String(32), default="0.1.0-demo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    sources: Mapped[list["ReportSource"]] = relationship(back_populates="report", cascade="all, delete-orphan")


class ReportSource(Base):
    """Links a generated report to the specific incident IDs that back each
    claim, so every statement is traceable to verified records."""

    __tablename__ = "report_sources"

    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)

    report: Mapped["Report"] = relationship(back_populates="sources")
