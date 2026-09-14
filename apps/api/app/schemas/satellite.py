import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class SatelliteScanRequest(BaseModel):
    latitude: float
    longitude: float


class ObservationOut(ORMModel):
    provider: str
    acquisition_date: datetime
    resolution_m: float
    cloud_coverage_pct: float
    is_simulated: bool


class NearbyFeatureOut(ORMModel):
    name: str
    distance_km: float


class SatelliteScanResult(ORMModel):
    """The 'HIGH-RISK AREA DETECTED' card. Every figure here is computed by
    the real risk engine and geospatial queries against the newly-persisted
    ai_detections row - only the underlying imagery/change signal itself is
    simulated (see `disclaimer`)."""

    ai_detection_id: uuid.UUID
    latitude: float
    longitude: float
    region: str | None
    district: str | None

    risk_score: int
    risk_category: str

    detection_type: str
    confidence: float
    estimated_area_hectares: float
    first_detected_days_ago: int

    nearest_water_body: NearbyFeatureOut | None
    nearest_protected_area: NearbyFeatureOut | None
    recommended_action: str

    previous_observation: ObservationOut
    current_observation: ObservationOut

    model_name: str
    model_version: str
    requires_verification: bool = True
    disclaimer: str = (
        "Change-detection analysis is SIMULATED for this demo (no live satellite "
        "feed is connected). The area view uses real current satellite imagery; "
        "the detection itself is an AI-generated signal requiring field "
        "verification, not confirmation of illegal activity."
    )


class SatelliteHistoryEntry(ORMModel):
    id: uuid.UUID
    detection_type: str
    confidence: float
    estimated_area_hectares: float | None
    observation_date: datetime
    review_status: str
    latitude: float
    longitude: float
