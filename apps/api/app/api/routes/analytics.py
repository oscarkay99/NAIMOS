from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def analytics_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("analytics:view")),
) -> dict:
    incidents_over_time = db.execute(text(
        """
        SELECT date_trunc('week', created_at)::date AS week, COUNT(*) AS count
        FROM incidents GROUP BY week ORDER BY week
        """
    )).mappings().all()

    by_region = db.execute(text(
        """
        SELECT r.name AS region, COUNT(*) AS count
        FROM incidents i JOIN regions r ON r.id = i.region_id
        GROUP BY r.name ORDER BY count DESC
        """
    )).mappings().all()

    by_status = db.execute(text(
        "SELECT status, COUNT(*) AS count FROM incidents GROUP BY status"
    )).mappings().all()

    verification_rate = db.execute(text(
        """
        SELECT
          COUNT(*) FILTER (WHERE verification_status = 'VERIFIED') AS verified,
          COUNT(*) AS total
        FROM incidents
        """
    )).mappings().one()

    workload = db.execute(text(
        """
        SELECT t.name AS team, COUNT(*) FILTER (WHERE a.status = 'ACTIVE') AS active,
               COUNT(*) FILTER (WHERE a.priority = 'HIGH' AND a.status = 'ACTIVE') AS high_priority,
               COUNT(*) FILTER (WHERE a.status = 'OVERDUE') AS overdue,
               COUNT(*) FILTER (WHERE a.status = 'COMPLETED') AS completed
        FROM assignments a JOIN teams t ON t.id = a.assigned_team_id
        GROUP BY t.name
        """
    )).mappings().all()

    return {
        "incidents_over_time": [dict(r) for r in incidents_over_time],
        "incidents_by_region": [dict(r) for r in by_region],
        "incidents_by_status": [dict(r) for r in by_status],
        "verification_rate": dict(verification_rate),
        "team_workload": [dict(r) for r in workload],
    }
