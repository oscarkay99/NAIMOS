import uuid
from datetime import datetime

from app.models.enums import RiskCategory
from app.schemas.common import ORMModel


class RiskFactorOut(ORMModel):
    label: str
    points: int
    detail: str | None


class RiskScoreOut(ORMModel):
    id: uuid.UUID
    incident_id: uuid.UUID | None
    score: int
    category: RiskCategory
    calculated_at: datetime
    model_version: str
    explanation: str | None
    factors: list[RiskFactorOut] = []
