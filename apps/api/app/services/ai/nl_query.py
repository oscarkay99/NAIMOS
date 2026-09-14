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

ROW_LIMIT = 50
QUERY_TIMEOUT_MS = 3000


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
    ("high_risk_unverified", re.compile(r"high[- ]risk.*(not|without).*(verif)", re.I)),
    ("incidents_near_water", re.compile(r"(near|close to).*(water|river|lake)", re.I)),
    ("region_summary", re.compile(r"summar\w* .*(region|western|eastern|ashanti|central|northern|volta|bono|ahafo|savannah|oti|upper)", re.I)),
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

    if intent == "region_summary":
        region_match = re.search(
            r"(western|eastern|ashanti|central|northern|volta|bono|ahafo|savannah|oti|upper)\w*", question, re.I
        )
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
