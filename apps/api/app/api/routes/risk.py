import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.ai import RiskScore
from app.models.incident import Incident
from app.models.user import User
from app.schemas.risk import RiskLeaderboardEntry, RiskRecalculateResult, RiskScoreOut
from app.services.audit import log_action
from app.services.geospatial.queries import nearest_water_body
from app.services.risk.engine import persist_risk_score, priority_label

router = APIRouter(prefix="/api/risk", tags=["risk"])

WEEK_OVER_WEEK_MIN_AGE_DAYS = 6


@router.get("/incidents/{incident_id}", response_model=RiskScoreOut)
def get_incident_risk(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("risk:view")),
) -> RiskScore:
    """Powers the 'Why is this area high risk?' breakdown (section 3)."""
    risk = db.execute(
        select(RiskScore)
        .options(selectinload(RiskScore.factors))
        .where(RiskScore.incident_id == incident_id)
        .order_by(RiskScore.calculated_at.desc())
    ).scalars().first()
    if risk is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No risk score calculated for this incident yet")
    return risk


@router.get("/leaderboard", response_model=list[RiskLeaderboardEntry])
def risk_leaderboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("risk:view")),
    limit: int = Query(20, le=100),
    include_closed: bool = Query(False),
) -> list[RiskLeaderboardEntry]:
    """The AI Risk Map: operational priority ranking across every monitored
    area, not just a single-location lookup. Answers 'where should we
    investigate first?' rather than just 'where is risk highest right now?'
    by also showing week-over-week change alongside the current score.
    """
    status_filter = "" if include_closed else "AND i.status NOT IN ('CLOSED', 'ARCHIVED')"

    rows = db.execute(
        text(
            f"""
            WITH latest AS (
                SELECT DISTINCT ON (incident_id) incident_id, score, category, calculated_at
                FROM risk_scores
                WHERE incident_id IS NOT NULL
                ORDER BY incident_id, calculated_at DESC
            ),
            past AS (
                SELECT DISTINCT ON (incident_id) incident_id, score AS past_score
                FROM risk_scores
                WHERE incident_id IS NOT NULL
                AND calculated_at <= NOW() - INTERVAL '{WEEK_OVER_WEEK_MIN_AGE_DAYS} days'
                ORDER BY incident_id, calculated_at DESC
            )
            SELECT i.id, i.reference_number, i.title, i.latitude, i.longitude, i.status,
                   r.name AS region, d.name AS district,
                   latest.score, latest.category, latest.calculated_at,
                   past.past_score
            FROM incidents i
            JOIN latest ON latest.incident_id = i.id
            LEFT JOIN past ON past.incident_id = i.id
            LEFT JOIN regions r ON r.id = i.region_id
            LEFT JOIN districts d ON d.id = i.district_id
            WHERE 1=1 {status_filter}
            ORDER BY latest.score DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()

    entries: list[RiskLeaderboardEntry] = []
    for row in rows:
        change_pct = None
        if row["past_score"] is not None and row["past_score"] > 0:
            change_pct = round((row["score"] - row["past_score"]) / row["past_score"] * 100, 1)

        water = nearest_water_body(db, row["latitude"], row["longitude"])
        label, emoji = priority_label(row["category"])

        entries.append(RiskLeaderboardEntry(
            incident_id=row["id"],
            reference_number=row["reference_number"],
            title=row["title"],
            region=row["region"],
            district=row["district"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            status=row["status"],
            score=row["score"],
            category=row["category"],
            calculated_at=row["calculated_at"],
            change_pct=change_pct,
            previous_score=row["past_score"],
            nearest_water_body_name=water["name"] if water else None,
            nearest_water_body_distance_km=round(water["distance_m"] / 1000, 2) if water else None,
            priority_label=label,
            priority_emoji=emoji,
        ))

    return entries


@router.post("/recalculate", response_model=RiskRecalculateResult)
def recalculate_all_risk_scores(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("risk:recalculate")),
) -> RiskRecalculateResult:
    """Runs a fresh risk-score pass across every active incident, appending
    a new risk_scores snapshot (never overwriting history) so the
    leaderboard's week-over-week change is computed from real data as the
    system is used repeatedly over time - not faked."""
    incidents = db.execute(
        select(Incident).where(Incident.status.notin_(["CLOSED", "ARCHIVED"]))
    ).scalars().all()

    now = datetime.now(timezone.utc)
    count = 0
    for incident in incidents:
        persist_risk_score(db, incident, calculated_at=now)
        count += 1

    log_action(
        db, user_id=user.id, action="risk.recalculated_all", entity_type="risk_scores", entity_id=None,
        new_value=f"{count} incidents recalculated",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return RiskRecalculateResult(recalculated_count=count, recalculated_at=now)
