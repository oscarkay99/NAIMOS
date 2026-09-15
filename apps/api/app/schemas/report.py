import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ReportGenerateRequest(BaseModel):
    report_type: str  # "executive_brief" | "weekly_situation" | "press_briefing" | "social_media_briefing"
    # | "parliamentary_briefing" | "talking_points" | "media_qa"
    region_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    date_from: date | None = None
    date_to: date | None = None


class ReportOut(ORMModel):
    id: uuid.UUID
    report_type: str
    title: str
    content_markdown: str
    model_name: str
    model_version: str
    source_incident_ids: list[uuid.UUID] = []
    created_at: datetime
