from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.user import User
from app.services.geospatial.queries import nearest_water_body
from app.services.risk.engine import priority_label

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


@router.get("/national-situation")
def national_situation(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("dashboard:national_situation")),
) -> dict:
    """Powers the PRO National Situation Room: a completely different view
    from the operational dashboard, answering 'what is happening across
    Ghana right now?' with a handful of top-level counts plus the top 10
    emerging hotspots. Every figure is a real database aggregate - nothing
    here is invented or interpolated."""
    summary = db.execute(text(
        """
        SELECT
          (SELECT COUNT(*) FROM investigations WHERE closed_at IS NULL) AS active_investigations,
          (SELECT COUNT(*) FROM incidents WHERE risk_score >= 61 AND status NOT IN ('CLOSED', 'ARCHIVED')) AS high_risk_locations,
          (SELECT COUNT(*) FROM assignments WHERE status = 'ACTIVE') AS field_operations,
          (SELECT COUNT(*) FROM incidents WHERE created_at >= date_trunc('month', NOW())) AS incidents_this_month,
          (SELECT COUNT(*) FROM incidents WHERE water_body_affected = TRUE) AS water_bodies_affected,
          (SELECT COUNT(*) FROM incidents WHERE protected_area_affected = TRUE) AS forest_areas_affected
        """
    )).mappings().one()

    hotspot_rows = db.execute(text(
        """
        WITH latest_risk AS (
            SELECT DISTINCT ON (incident_id) incident_id, score, category, calculated_at
            FROM risk_scores WHERE incident_id IS NOT NULL
            ORDER BY incident_id, calculated_at DESC
        ),
        past_risk AS (
            SELECT DISTINCT ON (incident_id) incident_id, score AS past_score
            FROM risk_scores WHERE incident_id IS NOT NULL
            AND calculated_at <= NOW() - INTERVAL '6 days'
            ORDER BY incident_id, calculated_at DESC
        ),
        latest_detection AS (
            SELECT DISTINCT ON (incident_id) incident_id, estimated_area_hectares
            FROM ai_detections WHERE incident_id IS NOT NULL AND estimated_area_hectares IS NOT NULL
            ORDER BY incident_id, observation_date DESC
        ),
        last_verification AS (
            SELECT DISTINCT ON (incident_id) incident_id, changed_at
            FROM incident_status_history WHERE new_status = 'VERIFIED'
            ORDER BY incident_id, changed_at DESC
        )
        SELECT i.id, i.reference_number, i.title, i.latitude, i.longitude, i.status,
               r.name AS region, d.name AS district,
               lr.score, lr.category, lr.calculated_at,
               pr.past_score, ld.estimated_area_hectares, lv.changed_at AS last_verified_at
        FROM incidents i
        JOIN latest_risk lr ON lr.incident_id = i.id
        LEFT JOIN past_risk pr ON pr.incident_id = i.id
        LEFT JOIN latest_detection ld ON ld.incident_id = i.id
        LEFT JOIN last_verification lv ON lv.incident_id = i.id
        LEFT JOIN regions r ON r.id = i.region_id
        LEFT JOIN districts d ON d.id = i.district_id
        WHERE i.status NOT IN ('CLOSED', 'ARCHIVED')
        ORDER BY lr.score DESC
        LIMIT 10
        """
    )).mappings().all()

    now = datetime.now(timezone.utc)
    hotspots = []
    for row in hotspot_rows:
        change_pct = None
        if row["past_score"] is not None and row["past_score"] > 0:
            change_pct = round((row["score"] - row["past_score"]) / row["past_score"] * 100, 1)
        water = nearest_water_body(db, row["latitude"], row["longitude"])
        label, emoji = priority_label(row["category"])
        last_verified_days_ago = (now - row["last_verified_at"]).days if row["last_verified_at"] else None

        hotspots.append({
            "incident_id": str(row["id"]),
            "reference_number": row["reference_number"],
            "title": row["title"],
            "region": row["region"],
            "district": row["district"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "risk_score": row["score"],
            "change_pct": change_pct,
            "estimated_affected_area_hectares": row["estimated_area_hectares"],
            "distance_to_water_m": round(water["distance_m"]) if water else None,
            "nearest_water_body_name": water["name"] if water else None,
            "last_field_verification_days_ago": last_verified_days_ago,
            "priority_label": label,
            "priority_emoji": emoji,
        })

    return {
        "active_investigations": summary["active_investigations"],
        "high_risk_locations": summary["high_risk_locations"],
        "field_operations": summary["field_operations"],
        "incidents_this_month": summary["incidents_this_month"],
        "water_bodies_affected": summary["water_bodies_affected"],
        "forest_areas_affected": summary["forest_areas_affected"],
        "top_hotspots": hotspots,
    }
