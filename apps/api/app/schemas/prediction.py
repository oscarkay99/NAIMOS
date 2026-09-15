import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import RiskCategory
from app.schemas.common import ORMModel


class ExpansionFactorOut(ORMModel):
    label: str
    points: int
    detail: str | None


class ExpansionPredictionOut(ORMModel):
    id: uuid.UUID
    incident_id: uuid.UUID | None
    probability: int
    category: RiskCategory
    expected_development: str
    recommendation: str
    calculated_at: datetime
    model_version: str
    explanation: str | None
    factors: list[ExpansionFactorOut] = []


class ExpansionLeaderboardEntry(ORMModel):
    """One row of the Predictive Galamsey Intelligence leaderboard: every
    active monitored area ranked by AI-estimated expansion probability."""

    incident_id: uuid.UUID
    reference_number: str
    title: str
    region: str | None
    district: str | None
    latitude: float
    longitude: float
    status: str

    probability: int
    category: RiskCategory
    expected_development: str
    recommendation: str
    calculated_at: datetime

    factors: list[ExpansionFactorOut] = []


class ExpansionRecalculateResult(BaseModel):
    recalculated_count: int
    recalculated_at: datetime
