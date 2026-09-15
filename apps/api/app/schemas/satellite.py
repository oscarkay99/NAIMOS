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
    the real risk engine and geospatial queries - only the underlying
    imagery/change signal itself may be simulated (see `disclaimer`,
    `is_simulated`). `change_detected=False` means real imagery was analyzed
    and nothing crossed the significance threshold - no ai_detections row is
    created in that case."""

    change_detected: bool
    is_simulated: bool

    ai_detection_id: uuid.UUID | None
    latitude: float
    longitude: float
    region: str | None
    district: str | None

    risk_score: int
    risk_category: str

    detection_type: str | None
    confidence: float | None
    estimated_area_hectares: float | None
    first_detected_days_ago: int | None

    nearest_water_body: NearbyFeatureOut | None
    nearest_protected_area: NearbyFeatureOut | None
    recommended_action: str

    previous_observation: ObservationOut
    current_observation: ObservationOut

    model_name: str
    model_version: str
    requires_verification: bool = True
    disclaimer: str


class SatelliteHistoryEntry(ORMModel):
    id: uuid.UUID
    detection_type: str
    confidence: float | None
    estimated_area_hectares: float | None
    observation_date: datetime
    review_status: str
    latitude: float
    longitude: float
