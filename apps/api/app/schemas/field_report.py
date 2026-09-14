import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class FieldReportCreate(BaseModel):
    incident_id: uuid.UUID | None = None
    latitude: float
    longitude: float
    narrative: str = ""
    captured_offline: bool = False


class VoiceExtraction(ORMModel):
    """Structured fields the AI pulled from a voice-note transcript (section 10).
    The officer must review and approve before it is stored as final."""

    time_mentioned: str | None = None
    equipment_mentioned: list[str] = []
    water_body_mentioned: str | None = None
    activity_summary: str | None = None
    status: str = "Requires verification"


class VoiceReportTranscribeOut(ORMModel):
    field_report_id: uuid.UUID
    transcript: str
    extraction: VoiceExtraction
    model_name: str
    model_version: str


class VoiceReportApprove(BaseModel):
    field_report_id: uuid.UUID
    edited_transcript: str | None = None
    edited_extraction: VoiceExtraction | None = None


class FieldReportOut(ORMModel):
    id: uuid.UUID
    incident_id: uuid.UUID | None
    officer_id: uuid.UUID
    latitude: float | None = None
    longitude: float | None = None
    narrative: str | None
    transcript: str | None
    ai_extraction: dict | None
    officer_approved: bool
    officer_approved_at: datetime | None
    captured_offline: bool
    created_at: datetime
