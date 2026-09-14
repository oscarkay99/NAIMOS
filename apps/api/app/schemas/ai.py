import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class AssistantQueryRequest(BaseModel):
    question: str


class AssistantQueryResponse(ORMModel):
    question: str
    detected_intent: str
    answer: str
    data: list[dict] = []
    row_count: int
    model_name: str
    model_version: str
    insufficient_data: bool = False


class AIDetectionOut(ORMModel):
    id: uuid.UUID
    detection_type: str
    confidence: float
    estimated_area_hectares: float | None
    observation_date: datetime
    requires_verification: bool
    review_status: str
    model_name: str
    model_version: str


class AIFeedbackRequest(BaseModel):
    review_status: str  # one of AIReviewStatus values
    note: str | None = None
