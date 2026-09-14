import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import InvestigationStage, Priority


class Team(Base, TimestampMixin):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    region_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"), nullable=True)

    officers: Mapped[list["Officer"]] = relationship(back_populates="team")


class Officer(Base, TimestampMixin):
    """Field-operations profile for a user (rank/team), separate from auth identity."""

    __tablename__ = "officers"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    rank: Mapped[str | None] = mapped_column(String(64), nullable=True)

    team: Mapped["Team"] = relationship(back_populates="officers")


class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = uuid_pk()
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[InvestigationStage] = mapped_column(
        Enum(InvestigationStage, name="investigation_stage"), default=InvestigationStage.REPORT
    )
    lead_officer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = uuid_pk()
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    priority: Mapped[Priority] = mapped_column(Enum(Priority, name="priority"), default=Priority.MEDIUM)
    assigned_team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    assigned_officer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    deadline: Mapped[date | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")  # ACTIVE | COMPLETED | OVERDUE | CANCELLED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Operation(Base, TimestampMixin):
    """A field operation/deployment, potentially spanning multiple incidents."""

    __tablename__ = "operations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    region_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"), nullable=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
