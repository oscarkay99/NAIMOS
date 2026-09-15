import uuid
from datetime import datetime

from pydantic import BaseModel

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


class RiskLeaderboardEntry(ORMModel):
    """One row of the AI Risk Map / leaderboard: operational priority
    ranking across all monitored areas, not just a single-location lookup."""

    incident_id: uuid.UUID
    reference_number: str
    title: str
    region: str | None
    district: str | None
    latitude: float
    longitude: float
    status: str

    score: int
    category: RiskCategory
    calculated_at: datetime

    change_pct: float | None  # week-over-week change; null if no prior snapshot exists
    previous_score: int | None

    nearest_water_body_name: str | None
    nearest_water_body_distance_km: float | None

    priority_label: str  # e.g. "Critical", "High", "Moderate", "Low"
    priority_emoji: str


class RiskRecalculateResult(BaseModel):
    recalculated_count: int
    recalculated_at: datetime
