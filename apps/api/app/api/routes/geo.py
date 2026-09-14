from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.enums import RiskCategory
from app.models.geo import District, Region
from app.models.incident import Incident
from app.models.user import User
from app.schemas.geo import DistrictOut, LocationIntelligence, MapFeature, RegionOut
from app.services.geospatial.queries import (
    count_nearby_incidents,
    district_for_point,
    nearest_protected_area,
    nearest_water_body,
)
from app.services.risk.engine import calculate_risk

router = APIRouter(prefix="/api", tags=["geo"])


@router.get("/regions", response_model=list[RegionOut])
def list_regions(db: Session = Depends(get_db), user: User = Depends(require_permission("incident:read"))) -> list[Region]:
    return list(db.execute(select(Region).order_by(Region.name)).scalars().all())


@router.get("/districts", response_model=list[DistrictOut])
def list_districts(
    region_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("incident:read")),
) -> list[District]:
    stmt = select(District).order_by(District.name)
    if region_id:
        stmt = stmt.where(District.region_id == region_id)
    return list(db.execute(stmt).scalars().all())


@router.get("/map/features", response_model=list[MapFeature])
def map_features(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("incident:read")),
) -> list[MapFeature]:
    """All point layers the map renders in one call: incidents/hotspots, water
    bodies, protected areas, forest reserves, AI detections. Kept lightweight
    (no geometry payload beyond lat/lon) so the client never loads unbounded
    raw geometry (section 53)."""
    features: list[MapFeature] = []

    for row in db.execute(text(
        "SELECT id, reference_number, title, latitude, longitude, status, risk_score FROM incidents"
    )).mappings():
        category = RiskCategory.from_score(row["risk_score"]).value if row["risk_score"] is not None else None
        features.append(MapFeature(
            id=str(row["id"]), layer="incident", name=f"{row['reference_number']} — {row['title']}",
            latitude=row["latitude"], longitude=row["longitude"], status=row["status"],
            risk_score=row["risk_score"], risk_category=category,
        ))

    for row in db.execute(text(
        "SELECT id, name, ST_Y(ST_Centroid(geom)) AS lat, ST_X(ST_Centroid(geom)) AS lon FROM water_bodies"
    )).mappings():
        features.append(MapFeature(id=str(row["id"]), layer="water_body", name=row["name"], latitude=row["lat"], longitude=row["lon"]))

    for row in db.execute(text(
        "SELECT id, name, ST_Y(ST_Centroid(geom)) AS lat, ST_X(ST_Centroid(geom)) AS lon FROM protected_areas"
    )).mappings():
        features.append(MapFeature(id=str(row["id"]), layer="protected_area", name=row["name"], latitude=row["lat"], longitude=row["lon"]))

    for row in db.execute(text(
        "SELECT id, name, ST_Y(ST_Centroid(geom)) AS lat, ST_X(ST_Centroid(geom)) AS lon FROM forest_reserves"
    )).mappings():
        features.append(MapFeature(id=str(row["id"]), layer="forest_reserve", name=row["name"], latitude=row["lat"], longitude=row["lon"]))

    for row in db.execute(text(
        "SELECT id, detection_type, confidence, ST_Y(location) AS lat, ST_X(location) AS lon FROM ai_detections"
    )).mappings():
        features.append(MapFeature(
            id=str(row["id"]), layer="ai_detection", name=f"AI: {row['detection_type']} ({row['confidence']:.0%})",
            latitude=row["lat"], longitude=row["lon"],
        ))

    return features


@router.get("/location-intelligence", response_model=LocationIntelligence)
def location_intelligence(
    lat: float = Query(...),
    lon: float = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("risk:view")),
) -> LocationIntelligence:
    """Section 59 — full intelligence card for an arbitrary map click."""
    located = district_for_point(db, lat, lon)
    risk = calculate_risk(db, lat, lon)

    water = nearest_water_body(db, lat, lon)
    protected = nearest_protected_area(db, lat, lon)

    recent_count = count_nearby_incidents(db, lat, lon, radius_km=5)
    total_count = count_nearby_incidents(db, lat, lon, radius_km=5)

    verified_count = db.execute(text(
        """
        SELECT COUNT(*) FROM incidents
        WHERE verification_status = 'VERIFIED'
        AND ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 5000)
        """
    ), {"lat": lat, "lon": lon}).scalar_one()

    detection_count = db.execute(text(
        """
        SELECT COUNT(*) FROM ai_detections
        WHERE ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 5000)
        """
    ), {"lat": lat, "lon": lon}).scalar_one()

    last_verification = db.execute(text(
        """
        SELECT MAX(changed_at) FROM incident_status_history ish
        JOIN incidents i ON i.id = ish.incident_id
        WHERE ish.new_status = 'VERIFIED'
        AND ST_DWithin(i.location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 5000)
        """
    ), {"lat": lat, "lon": lon}).scalar_one()

    recommended_action = "Field verification" if risk.score >= 41 else "Continue monitoring"

    return LocationIntelligence(
        latitude=lat,
        longitude=lon,
        region=located["region_name"] if located else None,
        district=located["name"] if located else None,
        risk_score=risk.score,
        risk_category=risk.category.value,
        risk_trend="increasing" if recent_count > 0 else "stable",
        nearest_water_body_name=water["name"] if water else None,
        nearest_water_body_distance_km=round(water["distance_m"] / 1000, 2) if water else None,
        nearest_protected_area_name=protected["name"] if protected else None,
        nearest_protected_area_distance_km=round(protected["distance_m"] / 1000, 2) if protected else None,
        historical_incident_count=total_count,
        ai_detection_count=detection_count,
        human_verified_incident_count=verified_count,
        last_field_verification=last_verification.isoformat() if last_verification else None,
        recommended_action=recommended_action,
    )
