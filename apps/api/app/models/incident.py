import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, now_utc, uuid_pk
from app.models.enums import (
    DataClassification,
    IncidentStatus,
    IncidentType,
    Priority,
    SourceType,
    VerificationStatus,
)


class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = uuid_pk()
    reference_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    location: Mapped[str] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    region_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"), nullable=True)
    district_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("districts.id"), nullable=True)
    community_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("communities.id"), nullable=True)

    incident_type: Mapped[IncidentType] = mapped_column(
        Enum(IncidentType, name="incident_type"), default=IncidentType.OTHER
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"), default=SourceType.FIELD_REPORT
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status"), default=IncidentStatus.NEW, nullable=False
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"), default=VerificationStatus.UNVERIFIED
    )
    priority: Mapped[Priority] = mapped_column(Enum(Priority, name="priority"), default=Priority.MEDIUM)
    classification: Mapped[DataClassification] = mapped_column(
        Enum(DataClassification, name="data_classification"), default=DataClassification.INTERNAL
    )

    environmental_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    water_body_affected: Mapped[bool] = mapped_column(Boolean, default=False)
    protected_area_affected: Mapped[bool] = mapped_column(Boolean, default=False)
    equipment_observed: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estimated_people_present: Mapped[int | None] = mapped_column(Integer, nullable=True)

    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_officer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    status_history: Mapped[list["IncidentStatusHistory"]] = relationship(
        back_populates="incident", order_by="IncidentStatusHistory.changed_at", cascade="all, delete-orphan"
    )
    region: Mapped["Region"] = relationship(foreign_keys=[region_id])
    district: Mapped["District"] = relationship(foreign_keys=[district_id])


class IncidentStatusHistory(Base):
    __tablename__ = "incident_status_history"

    id: Mapped[uuid.UUID] = uuid_pk()
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_status: Mapped[IncidentStatus | None] = mapped_column(Enum(IncidentStatus, name="incident_status"))
    new_status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus, name="incident_status"), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    incident: Mapped["Incident"] = relationship(back_populates="status_history")
