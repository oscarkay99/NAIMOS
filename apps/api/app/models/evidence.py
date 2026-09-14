import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, now_utc, uuid_pk
from app.models.enums import EvidenceFileType, VerificationStatus


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = uuid_pk()
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    file_type: Mapped[EvidenceFileType] = mapped_column(Enum(EvidenceFileType, name="evidence_file_type"))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    location: Mapped[str | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"), default=VerificationStatus.UNVERIFIED
    )

    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    versions: Mapped[list["EvidenceVersion"]] = relationship(
        back_populates="evidence", order_by="EvidenceVersion.version_number", cascade="all, delete-orphan"
    )


class EvidenceVersion(Base):
    """Immutable history of an evidence item. Replacing a file creates a new
    version rather than overwriting the original (section 11)."""

    __tablename__ = "evidence_versions"

    id: Mapped[uuid.UUID] = uuid_pk()
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    evidence: Mapped["Evidence"] = relationship(back_populates="versions")
