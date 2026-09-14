import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.ai import RiskScore
from app.models.user import User
from app.schemas.risk import RiskScoreOut

router = APIRouter(prefix="/api/risk", tags=["risk"])


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
