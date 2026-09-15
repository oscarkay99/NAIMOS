"""Controlled natural-language -> database pipeline (section 20).

    question -> intent detection -> ALLOWLISTED parametrized query -> execution
    on the read-only DB role -> row-limited result -> templated explanation

No AI-generated SQL is ever executed. Every intent below is a fixed,
hand-written, parametrized query; "AI" only decides which one applies and
fills in template wording around the real result set. If no intent matches,
the assistant says so rather than guessing.
"""

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.ai.voice_extraction import EQUIPMENT_TERMS

ROW_LIMIT = 50
QUERY_TIMEOUT_MS = 3000

REGION_NAMES = [
    "western", "eastern", "ashanti", "central", "northern", "volta",
    "bono", "ahafo", "savannah", "oti", "upper", "greater accra",
]
_REGION_ALTERNATION = "|".join(REGION_NAMES)
_EQUIPMENT_ALTERNATION = "|".join(EQUIPMENT_TERMS)


@dataclass
class QueryOutcome:
    intent: str
    sql_description: str
    rows: list[dict] = field(default_factory=list)


def _run(db: Session, sql: str, params: dict) -> list[dict]:
    db.execute(text(f"SET LOCAL statement_timeout = {QUERY_TIMEOUT_MS}"))
    result = db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]


_INTENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("districts_most_verified", re.compile(r"district.*(most|top).*verified", re.I)),
    ("emerging_hotspots", re.compile(r"emerging hotspot", re.I)),
    ("fastest_increasing_risk", re.compile(r"fastest.*increas|quickest.*increas", re.I)),
    ("top_n_field_verification", re.compile(r"top\s+\d+.*verif", re.I)),
    ("high_risk_unverified", re.compile(r"high[- ]risk.*(not|without).*(verif)", re.I)),
    # Specific (named water body + radius) must be checked before the generic "near water" pattern.
    ("incidents_near_named_water_time", re.compile(r"within\s+\d+(?:\.\d+)?\s*km.*(river|water|lake)", re.I)),
    ("incidents_near_water", re.compile(r"(near|close to).*(water|river|lake)", re.I)),
    # Equipment+region must be checked before the generic region_summary pattern.
    (
        "incidents_by_equipment_region",
        re.compile(rf"(incidents?|summar\w*|involv\w*).*({_EQUIPMENT_ALTERNATION})", re.I),
    ),
    ("region_summary", re.compile(rf"summar\w* .*({_REGION_ALTERNATION})", re.I)),
    ("open_over_n_days", re.compile(r"open (for )?(more than|over) (\d+) days?", re.I)),
    ("todays_briefing", re.compile(r"briefing.*(today|operations meeting)", re.I)),
]


def detect_intent(question: str) -> str | None:
    for intent, pattern in _INTENT_PATTERNS:
        if pattern.search(question):
            return intent
    return None


def run_intent(db: Session, intent: str, question: str) -> QueryOutcome:
    if intent == "districts_most_verified":
        rows = _run(
            db,
            """
            SELECT d.name AS district, r.name AS region, COUNT(*) AS verified_count
            FROM incidents i
            JOIN districts d ON d.id = i.district_id
            JOIN regions r ON r.id = d.region_id
            WHERE i.verification_status = 'VERIFIED'
            GROUP BY d.name, r.name
            ORDER BY verified_count DESC
            LIMIT :limit
            """,
            {"limit": ROW_LIMIT},
        )
        return QueryOutcome(intent, "Verified incidents grouped by district", rows)

    if intent == "emerging_hotspots":
        rows = _run(
            db,
            """
            SELECT rs.score, rs.category, rs.calculated_at,
                   i.reference_number, i.title, d.name AS district, r.name AS region
            FROM risk_scores rs
            JOIN incidents i ON i.id = rs.incident_id
            LEFT JOIN districts d ON d.id = i.district_id
            LEFT JOIN regions r ON r.id = i.region_id
            WHERE rs.score >= 61
            ORDER BY rs.calculated_at DESC
            LIMIT :limit
            """,
            {"limit": ROW_LIMIT},
        )
        return QueryOutcome(intent, "High/critical risk score locations, most recently calculated first", rows)

    if intent == "fastest_increasing_risk":
        rows = _run(
            db,
            """
            WITH latest AS (
                SELECT DISTINCT ON (incident_id) incident_id, score
                FROM risk_scores WHERE incident_id IS NOT NULL
                ORDER BY incident_id, calculated_at DESC
            ),
            past AS (
                SELECT DISTINCT ON (incident_id) incident_id, score AS past_score
                FROM risk_scores WHERE incident_id IS NOT NULL
                AND calculated_at <= NOW() - INTERVAL '6 days'
                ORDER BY incident_id, calculated_at DESC
            )
            SELECT i.reference_number, i.title, d.name AS district, r.name AS region,
                   latest.score AS current_score, past.past_score,
                   ROUND((((latest.score - past.past_score)::numeric / GREATEST(past.past_score, 1)) * 100), 1) AS change_pct
            FROM incidents i
            JOIN latest ON latest.incident_id = i.id
            JOIN past ON past.incident_id = i.id
            LEFT JOIN districts d ON d.id = i.district_id
            LEFT JOIN regions r ON r.id = i.region_id
            WHERE i.status NOT IN ('CLOSED', 'ARCHIVED')
            ORDER BY change_pct DESC
            LIMIT :limit
            """,
            {"limit": ROW_LIMIT},
        )
        return QueryOutcome(intent, "Areas with the largest week-over-week risk score increase", rows)

    if intent == "top_n_field_verification":
        n_match = re.search(r"top\s+(\d+)", question, re.I)
        n = min(int(n_match.group(1)) if n_match else 10, ROW_LIMIT)
        rows = _run(
            db,
            """
            SELECT i.reference_number, i.title, i.risk_score, d.name AS district, r.name AS region, i.created_at
            FROM incidents i
            LEFT JOIN districts d ON d.id = i.district_id
            LEFT JOIN regions r ON r.id = i.region_id
            WHERE i.verification_status != 'VERIFIED' AND i.status NOT IN ('CLOSED', 'ARCHIVED')
            AND i.created_at >= NOW() - INTERVAL '7 days'
            ORDER BY i.risk_score DESC NULLS LAST
            LIMIT :limit
            """,
            {"limit": n},
        )
        return QueryOutcome(intent, f"Top {n} locations from the last 7 days requiring field verification", rows)

    if intent == "high_risk_unverified":
        rows = _run(
            db,
            """
            SELECT i.reference_number, i.title, i.risk_score, d.name AS district, r.name AS region
            FROM incidents i
            LEFT JOIN districts d ON d.id = i.district_id
            LEFT JOIN regions r ON r.id = i.region_id
            WHERE i.risk_score >= 61 AND i.verification_status != 'VERIFIED'
            ORDER BY i.risk_score DESC
            LIMIT :limit
            """,
            {"limit": ROW_LIMIT},
        )
        return QueryOutcome(intent, "High-risk incidents that have not been field-verified", rows)

    if intent == "incidents_near_named_water_time":
        km_match = re.search(r"within\s+(\d+(?:\.\d+)?)\s*km", question, re.I)
        radius_km = float(km_match.group(1)) if km_match else 5.0
        river_match = re.search(r"(?:of|from)\s+(?:the\s+)?([A-Za-z]+)\s+(?:River|Lake)", question, re.I)
        river_term = river_match.group(1) if river_match else ""
        days_match = re.search(r"last\s+(\d+)\s+days?", question, re.I)
        days = int(days_match.group(1)) if days_match else 30

        if not river_term:
            # Couldn't identify which named water body was meant - say so
            # rather than silently searching near every water body instead.
            return QueryOutcome(intent, "Could not identify a named water body in the question", [])

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = _run(
            db,
            """
            SELECT i.reference_number, i.title, i.status, i.created_at, d.name AS district, wb.name AS water_body,
                   ROUND((ST_Distance(i.location::geography, wb.geom::geography) / 1000)::numeric, 2) AS distance_km
            FROM incidents i
            JOIN water_bodies wb ON wb.name ILIKE :water_pattern
            LEFT JOIN districts d ON d.id = i.district_id
            WHERE ST_DWithin(i.location::geography, wb.geom::geography, :radius_m)
            AND i.created_at >= :cutoff
            ORDER BY distance_km ASC
            LIMIT :limit
            """,
            {"water_pattern": f"%{river_term}%", "radius_m": radius_km * 1000, "cutoff": cutoff, "limit": ROW_LIMIT},
        )
        description = f"Incidents within {radius_km:g} km of a water body matching '{river_term}' in the last {days} days"
        return QueryOutcome(intent, description, rows)

    if intent == "incidents_near_water":
        rows = _run(
            db,
            """
            SELECT i.reference_number, i.title, i.status, d.name AS district
            FROM incidents i
            LEFT JOIN districts d ON d.id = i.district_id
            WHERE i.water_body_affected = true
            ORDER BY i.created_at DESC
            LIMIT :limit
            """,
            {"limit": ROW_LIMIT},
        )
        return QueryOutcome(intent, "Incidents flagged as affecting a water body", rows)

    if intent == "incidents_by_equipment_region":
        equipment_match = re.search(rf"({_EQUIPMENT_ALTERNATION})", question, re.I)
        equipment_term = equipment_match.group(1) if equipment_match else ""
        region_match = re.search(rf"({_REGION_ALTERNATION})\w*", question, re.I)
        region_term = region_match.group(1) if region_match else ""

        sql = """
            SELECT i.reference_number, i.title, i.status, i.equipment_observed, d.name AS district, r.name AS region
            FROM incidents i
            LEFT JOIN districts d ON d.id = i.district_id
            LEFT JOIN regions r ON r.id = i.region_id
            WHERE i.equipment_observed ILIKE :equipment_pattern
        """
        params: dict = {"equipment_pattern": f"%{equipment_term}%", "limit": ROW_LIMIT}
        if region_term:
            sql += " AND r.name ILIKE :region_pattern"
            params["region_pattern"] = f"%{region_term}%"
        sql += " ORDER BY i.created_at DESC LIMIT :limit"

        rows = _run(db, sql, params)
        description = f"Incidents with equipment matching '{equipment_term}'"
        if region_term:
            description += f" in region matching '{region_term}'"
        return QueryOutcome(intent, description, rows)

    if intent == "region_summary":
        region_match = re.search(rf"({_REGION_ALTERNATION})\w*", question, re.I)
        region_term = region_match.group(0) if region_match else ""
        rows = _run(
            db,
            """
            SELECT r.name AS region, i.status, COUNT(*) AS count
            FROM incidents i
            JOIN regions r ON r.id = i.region_id
            WHERE r.name ILIKE :region_pattern
            GROUP BY r.name, i.status
            ORDER BY count DESC
            LIMIT :limit
            """,
            {"region_pattern": f"%{region_term}%", "limit": ROW_LIMIT},
        )
        return QueryOutcome(intent, f"Incident counts by status for region matching '{region_term}'", rows)

    if intent == "open_over_n_days":
        days_match = re.search(r"(\d+)\s*days?", question)
        days = int(days_match.group(1)) if days_match else 14
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = _run(
            db,
            """
            SELECT i.reference_number, i.title, i.status, i.created_at, d.name AS district
            FROM incidents i
            LEFT JOIN districts d ON d.id = i.district_id
            WHERE i.status NOT IN ('CLOSED', 'ARCHIVED') AND i.created_at <= :cutoff
            ORDER BY i.created_at ASC
            LIMIT :limit
            """,
            {"cutoff": cutoff, "limit": ROW_LIMIT},
        )
        return QueryOutcome(intent, f"Open incidents older than {days} days", rows)

    if intent == "todays_briefing":
        rows = _run(
            db,
            """
            SELECT i.reference_number, i.title, i.status, i.priority, i.created_at, d.name AS district
            FROM incidents i
            LEFT JOIN districts d ON d.id = i.district_id
            WHERE i.created_at >= NOW() - INTERVAL '7 days'
            ORDER BY i.priority DESC, i.created_at DESC
            LIMIT :limit
            """,
            {"limit": ROW_LIMIT},
        )
        return QueryOutcome(intent, "Incidents from the last 7 days, ordered by priority", rows)

    raise ValueError(f"Unhandled intent: {intent}")


def format_answer(outcome: QueryOutcome) -> str:
    if not outcome.rows:
        return "Insufficient verified data. No records matched this query in the database."
    lines = [f"{outcome.sql_description} - {len(outcome.rows)} result(s):"]
    for row in outcome.rows[:10]:
        lines.append(" - " + ", ".join(f"{k}: {v}" for k, v in row.items()))
    if len(outcome.rows) > 10:
        lines.append(f"...and {len(outcome.rows) - 10} more.")
    return "\n".join(lines)
