import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.ai import ExpansionPrediction
from app.models.incident import Incident
from app.models.user import User
from app.schemas.prediction import (
    ExpansionFactorOut,
    ExpansionLeaderboardEntry,
    ExpansionPredictionOut,
    ExpansionRecalculateResult,
)
from app.services.audit import log_action
from app.services.prediction.engine import persist_expansion_prediction

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/incidents/{incident_id}", response_model=ExpansionPredictionOut)
def get_incident_prediction(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("prediction:view")),
) -> ExpansionPrediction:
    """Powers a per-location 'why might this expand?' breakdown, the
    predictive counterpart to /api/risk/incidents/{id}."""
    prediction = db.execute(
        select(ExpansionPrediction)
        .options(selectinload(ExpansionPrediction.factors))
        .where(ExpansionPrediction.incident_id == incident_id)
        .order_by(ExpansionPrediction.calculated_at.desc())
    ).scalars().first()
    if prediction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No expansion prediction calculated for this incident yet")
    return prediction


@router.get("/leaderboard", response_model=list[ExpansionLeaderboardEntry])
def prediction_leaderboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("prediction:view")),
    limit: int = Query(20, le=100),
) -> list[ExpansionLeaderboardEntry]:
    """Predictive Galamsey Intelligence: 'Emerging Threats' - every active
    monitored area ranked by AI-estimated near-term expansion probability,
    not by current risk. A location can rank high here even with a modest
    current risk score if it shows strong expansion signals (new access
    route, rising trend, equipment nearby)."""
    rows = db.execute(
        text(
            """
            WITH latest AS (
                SELECT DISTINCT ON (incident_id) id, incident_id, probability, category,
                       expected_development, recommendation, calculated_at
                FROM expansion_predictions
                WHERE incident_id IS NOT NULL
                ORDER BY incident_id, calculated_at DESC
            )
            SELECT i.id, i.reference_number, i.title, i.latitude, i.longitude, i.status,
                   r.name AS region, d.name AS district,
                   latest.id AS prediction_id, latest.probability, latest.category,
                   latest.expected_development, latest.recommendation, latest.calculated_at
            FROM incidents i
            JOIN latest ON latest.incident_id = i.id
            LEFT JOIN regions r ON r.id = i.region_id
            LEFT JOIN districts d ON d.id = i.district_id
            WHERE i.status NOT IN ('CLOSED', 'ARCHIVED')
            ORDER BY latest.probability DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()

    entries: list[ExpansionLeaderboardEntry] = []
    for row in rows:
        factor_rows = db.execute(
            text(
                """
                SELECT label, points, detail FROM expansion_prediction_factors
                WHERE prediction_id = :prediction_id
                ORDER BY points DESC
                """
            ),
            {"prediction_id": row["prediction_id"]},
        ).mappings().all()

        entries.append(ExpansionLeaderboardEntry(
            incident_id=row["id"],
            reference_number=row["reference_number"],
            title=row["title"],
            region=row["region"],
            district=row["district"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            status=row["status"],
            probability=row["probability"],
            category=row["category"],
            expected_development=row["expected_development"],
            recommendation=row["recommendation"],
            calculated_at=row["calculated_at"],
            factors=[ExpansionFactorOut(label=fr["label"], points=fr["points"], detail=fr["detail"]) for fr in factor_rows],
        ))

    return entries


@router.post("/recalculate", response_model=ExpansionRecalculateResult)
def recalculate_all_predictions(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("prediction:recalculate")),
) -> ExpansionRecalculateResult:
    """Runs a fresh expansion-prediction pass across every active incident,
    appending a new expansion_predictions snapshot (never overwriting
    history)."""
    incidents = db.execute(
        select(Incident).where(Incident.status.notin_(["CLOSED", "ARCHIVED"]))
    ).scalars().all()

    now = datetime.now(timezone.utc)
    count = 0
    for incident in incidents:
        persist_expansion_prediction(db, incident, calculated_at=now)
        count += 1

    log_action(
        db, user_id=user.id, action="prediction.recalculated_all", entity_type="expansion_predictions", entity_id=None,
        new_value=f"{count} incidents recalculated",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return ExpansionRecalculateResult(recalculated_count=count, recalculated_at=now)
