"""Predictive Galamsey Intelligence: an explainable, rule-based projection of
where illegal mining is likely to EXPAND next, not just where it is
happening today. Deliberately built on the same principles as the risk
engine (app/services/risk/engine.py) - every point on the probability is
attributable to a named, inspectable, database-backed signal. This is a
forward-looking estimate, never a certainty: probability is capped below
100 and every output states plainly that it requires field verification
before any operational or public claim is made from it.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.enums import RiskCategory
from app.services.geospatial.queries import nearest_other_incident, nearest_water_body

NEARBY_RADIUS_KM = 5.0
TREND_MIN_AGE_DAYS = 6
EQUIPMENT_WINDOW_DAYS = 30
MAX_PROBABILITY = 95  # never claim certainty about a future event


@dataclass
class ExpansionFactorResult:
    label: str
    points: int
    detail: str


@dataclass
class ExpansionResult:
    probability: int
    category: RiskCategory
    expected_development: str
    recommendation: str
    factors: list[ExpansionFactorResult]
    explanation: str


def _risk_trend_factor(db: Session, incident_id) -> ExpansionFactorResult | None:
    """Reuses the same risk-score history the AI Risk Map leaderboard reads
    for week-over-week Change% - if THIS location's own risk score is
    climbing, that's the strongest available signal of expansion."""
    if incident_id is None:
        return None
    row = db.execute(
        text(
            f"""
            WITH latest AS (
                SELECT score FROM risk_scores WHERE incident_id = :iid ORDER BY calculated_at DESC LIMIT 1
            ),
            past AS (
                SELECT score FROM risk_scores WHERE incident_id = :iid
                AND calculated_at <= NOW() - INTERVAL '{TREND_MIN_AGE_DAYS} days'
                ORDER BY calculated_at DESC LIMIT 1
            )
            SELECT latest.score AS latest_score, past.score AS past_score FROM latest, past
            """
        ),
        {"iid": str(incident_id)},
    ).mappings().first()
    if not row or row["past_score"] in (None, 0) or row["latest_score"] is None:
        return None
    change_pct = (row["latest_score"] - row["past_score"]) / row["past_score"] * 100
    if change_pct <= 15:
        return None
    pts = min(round(change_pct / 2), 30)
    return ExpansionFactorResult(
        "Mining activity increasing", pts, f"Risk score increased {change_pct:.1f}% over the past week"
    )


def _new_access_route_factor(db: Session, lat: float, lon: float) -> ExpansionFactorResult | None:
    count = db.execute(
        text(
            """
            SELECT COUNT(*) FROM ai_detections
            WHERE detection_type = 'NEW_ROAD' AND review_status != 'REJECTED'
            AND ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
            """
        ),
        {"lat": lat, "lon": lon, "radius_m": NEARBY_RADIUS_KM * 1000},
    ).scalar_one()
    if not count:
        return None
    return ExpansionFactorResult(
        "New access route detected", 20,
        f"{count} AI-flagged new access route signal(s) within {NEARBY_RADIUS_KM:g} km - requires field verification",
    )


def _land_disturbance_factor(db: Session, lat: float, lon: float) -> ExpansionFactorResult | None:
    count = db.execute(
        text(
            """
            SELECT COUNT(*) FROM ai_detections
            WHERE detection_type != 'NEW_ROAD' AND review_status != 'REJECTED'
            AND ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
            """
        ),
        {"lat": lat, "lon": lon, "radius_m": NEARBY_RADIUS_KM * 1000},
    ).scalar_one()
    if not count:
        return None
    pts = min(count * 8, 20)
    return ExpansionFactorResult(
        "Increased land disturbance", pts,
        f"{count} AI-detected land-disturbance signal(s) nearby (vegetation loss / exposed soil / excavation)",
    )


def _prior_activity_factor(db: Session, lat: float, lon: float, exclude_id) -> ExpansionFactorResult | None:
    nearest = nearest_other_incident(db, lat, lon, exclude_id)
    if not nearest:
        return None
    dist_km = nearest["distance_m"] / 1000
    if dist_km > NEARBY_RADIUS_KM:
        return None
    pts = 15 if dist_km <= 1 else 8 if dist_km <= 3 else 4
    return ExpansionFactorResult(
        "Previous mining activity nearby", pts,
        f"Prior incident `{nearest['reference_number']}` recorded {dist_km:.1f} km away",
    )


def _water_proximity_factor(db: Session, lat: float, lon: float) -> ExpansionFactorResult | None:
    water = nearest_water_body(db, lat, lon)
    if not water:
        return None
    dist_km = water["distance_m"] / 1000
    if dist_km <= 0.5:
        pts = 12
    elif dist_km <= 2:
        pts = 6
    else:
        return None
    return ExpansionFactorResult("Proximity to water body", pts, f"{water['name']} is {dist_km:.2f} km away")


def _equipment_movement_factor(db: Session, lat: float, lon: float, exclude_id) -> ExpansionFactorResult | None:
    query = """
        SELECT COUNT(*) FROM incidents
        WHERE equipment_observed IS NOT NULL AND created_at >= :since
        AND ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
    """
    params = {
        "lat": lat, "lon": lon, "radius_m": NEARBY_RADIUS_KM * 1000,
        "since": datetime.now(timezone.utc) - timedelta(days=EQUIPMENT_WINDOW_DAYS),
    }
    if exclude_id is not None:
        query += " AND id != :exclude_id"
        params["exclude_id"] = str(exclude_id)
    count = db.execute(text(query), params).scalar_one()
    if not count:
        return None
    pts = min(count * 6, 15)
    return ExpansionFactorResult(
        "Equipment movement reports", pts,
        f"{count} report(s) within {NEARBY_RADIUS_KM:g} km in the last {EQUIPMENT_WINDOW_DAYS} days noted equipment on site",
    )


_DEVELOPMENT_BRACKETS = [
    (70, "1-2 weeks", "Conduct verification patrol before significant expansion occurs. High priority."),
    (50, "2-4 weeks", "Conduct verification patrol before significant expansion occurs."),
    (30, "4-8 weeks", "Schedule verification patrol within routine rotation."),
]
_DEFAULT_DEVELOPMENT = ("No imminent expansion signal", "Continue passive monitoring; no immediate patrol required.")


def calculate_expansion(db: Session, lat: float, lon: float, incident_id=None) -> ExpansionResult:
    """`incident_id`, when given, is used both to read that location's own
    risk-score trend and to exclude it from nearby-incident counts."""
    factors: list[ExpansionFactorResult] = []

    for factor in (
        _risk_trend_factor(db, incident_id),
        _new_access_route_factor(db, lat, lon),
        _land_disturbance_factor(db, lat, lon),
        _prior_activity_factor(db, lat, lon, incident_id),
        _water_proximity_factor(db, lat, lon),
        _equipment_movement_factor(db, lat, lon, incident_id),
    ):
        if factor is not None:
            factors.append(factor)

    probability = min(sum(f.points for f in factors), MAX_PROBABILITY)
    category = RiskCategory.from_score(probability)

    expected_development, recommendation = _DEFAULT_DEVELOPMENT
    for threshold, development, rec in _DEVELOPMENT_BRACKETS:
        if probability >= threshold:
            expected_development, recommendation = development, rec
            break

    if factors:
        breakdown = "; ".join(f"+{f.points} {f.label.lower()}" for f in factors)
        explanation = (
            f"EXPANSION PROBABILITY: {probability}% ({category.value}). Contributing factors: {breakdown}. "
            "This is an AI-generated projection based on current signals, not a certainty about future "
            "events - always requires field verification before any operational or public claim."
        )
    else:
        explanation = (
            "EXPANSION PROBABILITY: 0% (LOW). No expansion signals found near this location. "
            "This is an AI-generated projection, not a certainty about future events."
        )

    return ExpansionResult(
        probability=probability, category=category, expected_development=expected_development,
        recommendation=recommendation, factors=factors, explanation=explanation,
    )


def persist_expansion_prediction(db: Session, incident, calculated_at: datetime | None = None) -> ExpansionResult:
    """Computes and persists a new expansion_predictions snapshot (+ factors)
    for an incident's location. Never overwrites prior snapshots - each call
    appends to history, mirroring persist_risk_score."""
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point

    from app.models.ai import ExpansionPrediction, ExpansionPredictionFactor

    result = calculate_expansion(db, incident.latitude, incident.longitude, incident_id=incident.id)
    prediction = ExpansionPrediction(
        incident_id=incident.id,
        location=from_shape(Point(incident.longitude, incident.latitude), srid=4326),
        probability=result.probability,
        category=result.category,
        expected_development=result.expected_development,
        recommendation=result.recommendation,
        calculated_at=calculated_at or datetime.now(timezone.utc),
        explanation=result.explanation,
    )
    db.add(prediction)
    db.flush()
    for f in result.factors:
        db.add(ExpansionPredictionFactor(
            prediction_id=prediction.id, label=f.label, points=f.points, detail=f.detail
        ))
    return result
