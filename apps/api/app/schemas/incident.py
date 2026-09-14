import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import (
    DataClassification,
    IncidentStatus,
    IncidentType,
    Priority,
    SourceType,
    VerificationStatus,
)
from app.schemas.common import ORMModel


class IncidentCreate(BaseModel):
    title: str
    description: str = ""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    region_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    community_id: uuid.UUID | None = None
    incident_type: IncidentType = IncidentType.OTHER
    environmental_impact: str | None = None
    water_body_affected: bool = False
    protected_area_affected: bool = False
    equipment_observed: str | None = None
    estimated_people_present: int | None = None
    priority: Priority = Priority.MEDIUM
    classification: DataClassification = DataClassification.INTERNAL


class IncidentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    incident_type: IncidentType | None = None
    environmental_impact: str | None = None
    water_body_affected: bool | None = None
    protected_area_affected: bool | None = None
    equipment_observed: str | None = None
    estimated_people_present: int | None = None
    priority: Priority | None = None
    assigned_officer_id: uuid.UUID | None = None


class StatusChangeRequest(BaseModel):
    new_status: IncidentStatus
    reason: str


class IncidentStatusHistoryOut(ORMModel):
    id: uuid.UUID
    previous_status: IncidentStatus | None
    new_status: IncidentStatus
    changed_by: uuid.UUID | None
    reason: str | None
    changed_at: datetime


class IncidentOut(ORMModel):
    id: uuid.UUID
    reference_number: str
    title: str
    description: str
    latitude: float
    longitude: float
    region_id: uuid.UUID | None
    district_id: uuid.UUID | None
    incident_type: IncidentType
    source_type: SourceType
    status: IncidentStatus
    verification_status: VerificationStatus
    priority: Priority
    classification: DataClassification
    water_body_affected: bool
    protected_area_affected: bool
    equipment_observed: str | None
    estimated_people_present: int | None
    risk_score: int | None
    is_demo: bool
    assigned_officer_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class IncidentDetailOut(IncidentOut):
    status_history: list[IncidentStatusHistoryOut] = []
