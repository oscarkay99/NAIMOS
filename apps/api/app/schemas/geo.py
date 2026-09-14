import uuid

from app.schemas.common import ORMModel


class RegionOut(ORMModel):
    id: uuid.UUID
    name: str
    capital: str | None


class DistrictOut(ORMModel):
    id: uuid.UUID
    region_id: uuid.UUID
    name: str
    capital: str | None


class MapFeature(ORMModel):
    """A single point-like feature for the map layers (incident, hotspot, water
    body centroid, protected area centroid, etc.) rendered as GeoJSON on the client."""

    id: str
    layer: str  # "incident" | "water_body" | "protected_area" | "forest_reserve" | "ai_detection"
    name: str
    latitude: float
    longitude: float
    status: str | None = None
    risk_score: int | None = None
    risk_category: str | None = None


class LocationIntelligence(ORMModel):
    """Section 59 — full context for a selected map location."""

    latitude: float
    longitude: float
    region: str | None
    district: str | None
    risk_score: int | None
    risk_category: str | None
    risk_trend: str  # "increasing" | "stable" | "decreasing" | "unknown"
    nearest_water_body_name: str | None
    nearest_water_body_distance_km: float | None
    nearest_protected_area_name: str | None
    nearest_protected_area_distance_km: float | None
    historical_incident_count: int
    ai_detection_count: int
    human_verified_incident_count: int
    last_field_verification: str | None
    recommended_action: str
