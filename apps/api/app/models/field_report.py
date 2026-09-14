import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk


class FieldReport(Base, TimestampMixin):
    """A report submitted by a field officer, optionally captured via voice."""

    __tablename__ = "field_reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    officer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)

    location: Mapped[str | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Voice-to-report pipeline (section 10): original audio is never mutated.
    original_audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_extraction: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    officer_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    officer_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    captured_offline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped["Incident"] = relationship()
