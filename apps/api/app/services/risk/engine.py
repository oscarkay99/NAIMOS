"""Explainable, rule-based Operational Risk / Investigation Priority Score
(spec section 3). This is deliberately NOT a black box: every point on the
0-100 score is attributable to a named, inspectable factor, and the score
represents where human investigation should be prioritized - never a
certainty that illegal mining is occurring.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.enums import RiskCategory
from app.services.geospatial.queries import nearest_protected_area, nearest_water_body

RECENT_WINDOW_DAYS = 30
NEARBY_RADIUS_KM = 5.0

PRIORITY_LABELS: dict[RiskCategory, tuple[str, str]] = {
    RiskCategory.CRITICAL: ("Critical", "\U0001F534"),  # red circle
    RiskCategory.HIGH: ("High", "\U0001F7E0"),  # orange circle
    RiskCategory.ELEVATED: ("Elevated", "\U0001F7E0"),  # orange circle
    RiskCategory.MODERATE: ("Moderate", "\U0001F7E1"),  # yellow circle
    RiskCategory.LOW: ("Low", "\U0001F7E2"),  # green circle
}


def priority_label(category: RiskCategory) -> tuple[str, str]:
    return PRIORITY_LABELS[category]


@dataclass
class RiskFactorResult:
    label: str
    points: int
    detail: str


@dataclass
class RiskResult:
    score: int
    category: RiskCategory
    factors: list[RiskFactorResult]
    explanation: str


def _recent_incident_count(db: Session, lat: float, lon: float, exclude_id=None) -> int:
    query = """
        SELECT COUNT(*) FROM incidents
        WHERE created_at >= :since
        AND ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
    """
    params = {
        "since": datetime.now(timezone.utc) - timedelta(days=RECENT_WINDOW_DAYS),
        "lat": lat,
        "lon": lon,
        "radius_m": NEARBY_RADIUS_KM * 1000,
    }
    if exclude_id is not None:
        query += " AND id != :exclude_id"
        params["exclude_id"] = str(exclude_id)
    return db.execute(text(query), params).scalar_one()


def _historical_incident_count(db: Session, lat: float, lon: float, exclude_id=None) -> int:
    query = """
        SELECT COUNT(*) FROM incidents
        WHERE created_at < :since
        AND ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
    """
    params = {
        "since": datetime.now(timezone.utc) - timedelta(days=RECENT_WINDOW_DAYS),
        "lat": lat,
        "lon": lon,
        "radius_m": NEARBY_RADIUS_KM * 1000,
    }
    if exclude_id is not None:
        query += " AND id != :exclude_id"
        params["exclude_id"] = str(exclude_id)
    return db.execute(text(query), params).scalar_one()


def _ai_detection_count(db: Session, lat: float, lon: float) -> int:
    row = db.execute(
        text(
            """
            SELECT COUNT(*) FROM ai_detections
            WHERE ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
            """
        ),
        {"lat": lat, "lon": lon, "radius_m": NEARBY_RADIUS_KM * 1000},
    ).scalar_one()
    return row


def calculate_risk(db: Session, lat: float, lon: float, exclude_incident_id=None) -> RiskResult:
    factors: list[RiskFactorResult] = []

    recent = _recent_incident_count(db, lat, lon, exclude_incident_id)
    if recent:
        pts = min(recent * 8, 25)
        factors.append(RiskFactorResult(
            "Recent field reports", pts, f"{recent} report(s) within {NEARBY_RADIUS_KM:g} km in the last {RECENT_WINDOW_DAYS} days"
        ))

    historical = _historical_incident_count(db, lat, lon, exclude_incident_id)
    if historical:
        pts = min(historical * 4, 15)
        factors.append(RiskFactorResult(
            "Historical activity", pts, f"{historical} prior incident(s) recorded within {NEARBY_RADIUS_KM:g} km"
        ))

    detections = _ai_detection_count(db, lat, lon)
    if detections:
        pts = min(detections * 10, 20)
        factors.append(RiskFactorResult(
            "AI-detected land disturbance signals", pts,
            f"{detections} unverified AI change-detection signal(s) nearby - requires field verification"
        ))

    water = nearest_water_body(db, lat, lon)
    if water is not None:
        dist_km = water["distance_m"] / 1000
        if dist_km <= 0.5:
            factors.append(RiskFactorResult("Proximity to water body", 15, f"{water['name']} is {dist_km:.2f} km away"))
        elif dist_km <= 2:
            factors.append(RiskFactorResult("Proximity to water body", 8, f"{water['name']} is {dist_km:.2f} km away"))

    protected = nearest_protected_area(db, lat, lon)
    if protected is not None:
        dist_km = protected["distance_m"] / 1000
        if dist_km <= 0.5:
            factors.append(RiskFactorResult("Proximity to protected/forest area", 15, f"{protected['name']} is {dist_km:.2f} km away"))
        elif dist_km <= 2:
            factors.append(RiskFactorResult("Proximity to protected/forest area", 8, f"{protected['name']} is {dist_km:.2f} km away"))

    if recent > historical and recent >= 2:
        factors.append(RiskFactorResult("Activity increasing", 5, "More reports in the recent window than in prior history"))

    score = min(sum(f.points for f in factors), 100)
    category = RiskCategory.from_score(score)

    if factors:
        breakdown = "; ".join(f"+{f.points} {f.label.lower()}" for f in factors)
        explanation = (
            f"RISK SCORE: {score} ({category.value}). Contributing factors: {breakdown}. "
            "This is an operational investigation-priority score, not confirmation of illegal activity."
        )
    else:
        explanation = (
            "RISK SCORE: 0 (LOW). No contributing risk signals found near this location. "
            "This is an operational investigation-priority score, not confirmation of illegal activity."
        )

    return RiskResult(score=score, category=category, factors=factors, explanation=explanation)


def persist_risk_score(db: Session, incident, calculated_at: datetime | None = None) -> "RiskResult":
    """Computes and persists a new risk_scores snapshot (+ factors) for an
    incident's location, updating the incident's denormalized `risk_score`.
    Never overwrites prior snapshots - each call appends to history, which
    is what makes week-over-week change on the leaderboard real rather than
    synthetic. Shared by incident creation and the bulk recalculate endpoint."""
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point

    from app.models.ai import RiskFactor, RiskScore

    result = calculate_risk(db, incident.latitude, incident.longitude, exclude_incident_id=incident.id)
    risk_score = RiskScore(
        incident_id=incident.id,
        location=from_shape(Point(incident.longitude, incident.latitude), srid=4326),
        score=result.score,
        category=result.category,
        calculated_at=calculated_at or datetime.now(timezone.utc),
        explanation=result.explanation,
    )
    db.add(risk_score)
    db.flush()
    for f in result.factors:
        db.add(RiskFactor(risk_score_id=risk_score.id, label=f.label, points=f.points, detail=f.detail))
    incident.risk_score = result.score
    return result
