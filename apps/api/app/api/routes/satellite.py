import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.ai import AIDetection
from app.models.enums import AIReviewStatus, DetectionType
from app.models.satellite import SatelliteObservation, SatelliteScan
from app.models.user import User
from app.schemas.satellite import (
    NearbyFeatureOut,
    ObservationOut,
    SatelliteHistoryEntry,
    SatelliteScanRequest,
    SatelliteScanResult,
)
from app.services.audit import log_action
from app.services.geospatial.queries import district_for_point, nearest_protected_area, nearest_water_body
from app.services.risk.engine import calculate_risk
from app.services.satellite.provider import SatelliteProviderError, get_satellite_provider

SIMULATED_DISCLAIMER = (
    "Change-detection analysis is SIMULATED for this demo (no live satellite "
    "feed is connected). The area view uses real current satellite imagery; "
    "the detection itself is an AI-generated signal requiring field "
    "verification, not confirmation of illegal activity."
)
REAL_DISCLAIMER = (
    "Change-detection analysis uses real Sentinel-2 imagery via Sentinel Hub. "
    "This is an AI-generated signal requiring field verification, not "
    "confirmation of illegal activity."
)

router = APIRouter(prefix="/api/satellite", tags=["satellite"])

NEARBY_RADIUS_M = 5000


def _save_observation(db: Session, lat: float, lon: float, obs) -> SatelliteObservation:
    row = SatelliteObservation(
        location=from_shape(Point(lon, lat), srid=4326),
        provider=obs.provider,
        acquisition_date=obs.acquisition_date,
        resolution_m=obs.resolution_m,
        cloud_coverage_pct=obs.cloud_coverage_pct,
        is_simulated=obs.is_simulated,
    )
    db.add(row)
    db.flush()
    return row


@router.post("/scan", response_model=SatelliteScanResult)
def run_scan(
    payload: SatelliteScanRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("satellite:scan")),
) -> SatelliteScanResult:
    """Runs an AI change-detection scan against an AOI (section 6/7/58).

    This persists real rows through the same path a production satellite
    pipeline would use: two SatelliteObservation rows (before/after imagery
    metadata), an AIDetection row, and a SatelliteScan linking them - so the
    resulting risk score, map marker, and audit trail are genuinely computed
    by the existing engine, not mocked in the response.
    """
    lat, lon = payload.latitude, payload.longitude

    # Earliest known signal at this AOI *before* this scan, to report
    # "first detected N days ago" the way a real expanding-hotspot story
    # would look once multiple passes accumulate.
    earliest_existing = db.execute(
        text(
            """
            SELECT MIN(observation_date) FROM ai_detections
            WHERE ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
            """
        ),
        {"lat": lat, "lon": lon, "radius_m": NEARBY_RADIUS_M},
    ).scalar_one()

    provider = get_satellite_provider()
    try:
        result = provider.detect_change(lat, lon)
    except SatelliteProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    previous_obs = _save_observation(db, lat, lon, result.previous_observation)
    current_obs = _save_observation(db, lat, lon, result.current_observation)

    detection = None
    if result.change_detected:
        detection = AIDetection(
            location=from_shape(Point(lon, lat), srid=4326),
            detection_type=DetectionType(result.detection_type),
            confidence=result.confidence,
            estimated_area_hectares=result.estimated_area_hectares,
            observation_date=result.current_observation.acquisition_date,
            previous_observation_date=result.previous_observation.acquisition_date,
            source="satellite_scan",
            requires_verification=True,
            review_status=AIReviewStatus.PENDING,
            model_name=provider.name,
            model_version="0.1.0-demo",
        )
        db.add(detection)
        db.flush()

    db.add(SatelliteScan(
        location=from_shape(Point(lon, lat), srid=4326),
        previous_observation_id=previous_obs.id,
        current_observation_id=current_obs.id,
        ai_detection_id=detection.id if detection else None,
        requested_by=user.id,
        model_name=provider.name,
    ))

    # Real risk computation either way - proximity/history signals still apply
    # even when this particular scan found nothing new.
    risk = calculate_risk(db, lat, lon)
    located = district_for_point(db, lat, lon)
    water = nearest_water_body(db, lat, lon)
    protected = nearest_protected_area(db, lat, lon)

    first_detected_days_ago = None
    if detection is not None:
        first_detected_days_ago = 0
        if earliest_existing is not None:
            first_detected_days_ago = max(
                (datetime.now(timezone.utc) - earliest_existing.replace(tzinfo=timezone.utc)).days, 0
            )

    recommended_action = "Field verification" if risk.score >= 41 else "Continue monitoring"

    log_action(
        db, user_id=user.id, action="satellite.scan",
        entity_type="ai_detection", entity_id=str(detection.id) if detection else None,
        new_value=(
            f"{result.detection_type} ({result.confidence:.0%}, {result.estimated_area_hectares} ha)"
            if result.change_detected else "no significant change detected"
        ),
        metadata={"latitude": lat, "longitude": lon, "risk_score": risk.score, "provider": provider.name},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return SatelliteScanResult(
        change_detected=result.change_detected,
        is_simulated=result.current_observation.is_simulated,
        ai_detection_id=detection.id if detection else None,
        latitude=lat,
        longitude=lon,
        region=located["region_name"] if located else None,
        district=located["name"] if located else None,
        risk_score=risk.score,
        risk_category=risk.category.value,
        detection_type=result.detection_type,
        confidence=result.confidence,
        estimated_area_hectares=result.estimated_area_hectares,
        first_detected_days_ago=first_detected_days_ago,
        nearest_water_body=NearbyFeatureOut(name=water["name"], distance_km=round(water["distance_m"] / 1000, 2)) if water else None,
        nearest_protected_area=NearbyFeatureOut(name=protected["name"], distance_km=round(protected["distance_m"] / 1000, 2)) if protected else None,
        recommended_action=recommended_action,
        previous_observation=ObservationOut(
            provider=result.previous_observation.provider,
            acquisition_date=result.previous_observation.acquisition_date,
            resolution_m=result.previous_observation.resolution_m,
            cloud_coverage_pct=result.previous_observation.cloud_coverage_pct,
            is_simulated=result.previous_observation.is_simulated,
        ),
        current_observation=ObservationOut(
            provider=result.current_observation.provider,
            acquisition_date=result.current_observation.acquisition_date,
            resolution_m=result.current_observation.resolution_m,
            cloud_coverage_pct=result.current_observation.cloud_coverage_pct,
            is_simulated=result.current_observation.is_simulated,
        ),
        model_name=provider.name,
        model_version="0.1.0-demo",
        disclaimer=SIMULATED_DISCLAIMER if result.current_observation.is_simulated else REAL_DISCLAIMER,
    )


@router.get("/status")
def satellite_status(
    user: User = Depends(require_permission("satellite:scan")),
) -> dict:
    provider = get_satellite_provider()
    return {"provider_name": provider.name, "is_simulated": provider.is_simulated}


@router.get("/history", response_model=list[SatelliteHistoryEntry])
def scan_history(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(5.0),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("satellite:scan")),
) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT id, detection_type, confidence, estimated_area_hectares, observation_date,
                   review_status, ST_Y(location) AS latitude, ST_X(location) AS longitude
            FROM ai_detections
            WHERE source = 'satellite_scan'
            AND ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
            ORDER BY observation_date DESC
            """
        ),
        {"lat": lat, "lon": lon, "radius_m": radius_km * 1000},
    ).mappings().all()
    return [_sanitize_nan(dict(r)) for r in rows]


def _sanitize_nan(row: dict) -> dict:
    """Defense in depth: a NaN float would otherwise crash JSON
    serialization for the whole response rather than just this one row -
    normalize any stray NaN (legacy bad data, a future provider bug) to
    None so a single corrupted record can't take the endpoint down."""
    for key, value in row.items():
        if isinstance(value, float) and math.isnan(value):
            row[key] = None
    return row
