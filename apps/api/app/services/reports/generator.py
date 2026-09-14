"""Report / PRO communications generator (sections 16-18). Every figure in the
output is pulled directly from the database — never invented. Output always
separates VERIFIED FACTS from AI-GENERATED INTERPRETATION and cites the
backing incident IDs so a human can trace every claim."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import IncidentStatus, VerificationStatus
from app.models.incident import Incident

REPORT_TITLES = {
    "executive_brief": "Executive Brief",
    "press_briefing": "Press Briefing",
    "weekly_situation": "Weekly Situation Summary",
    "talking_points": "Talking Points",
    "media_qa": "Media Q&A Preparation",
}


@dataclass
class GeneratedReport:
    title: str
    content_markdown: str
    source_incident_ids: list[str]


def _apply_filters(stmt, region_id, district_id, date_from: date | None, date_to: date | None):
    if region_id:
        stmt = stmt.where(Incident.region_id == region_id)
    if district_id:
        stmt = stmt.where(Incident.district_id == district_id)
    if date_from:
        stmt = stmt.where(Incident.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Incident.created_at <= date_to)
    return stmt


def generate_report(
    db: Session, report_type: str, region_id, district_id, date_from: date | None, date_to: date | None
) -> GeneratedReport:
    stmt = _apply_filters(select(Incident), region_id, district_id, date_from, date_to)
    incidents = list(db.execute(stmt).scalars().all())

    if not incidents:
        return GeneratedReport(
            title=REPORT_TITLES.get(report_type, "Report"),
            content_markdown=(
                "## Insufficient verified data\n\n"
                "No incidents matched the selected filters. No report can be generated "
                "from an empty result set — figures are never fabricated."
            ),
            source_incident_ids=[],
        )

    verified = [i for i in incidents if i.verification_status == VerificationStatus.VERIFIED]
    unverified = [i for i in incidents if i.verification_status != VerificationStatus.VERIFIED]
    high_risk = [i for i in incidents if (i.risk_score or 0) >= 61]
    environmental = [i for i in incidents if i.water_body_affected or i.protected_area_affected]
    open_investigations = [i for i in incidents if i.status not in (IncidentStatus.CLOSED, IncidentStatus.ARCHIVED)]
    recent_cutoff = datetime.now(timezone.utc).date()
    recent = sorted(incidents, key=lambda i: i.created_at, reverse=True)[:5]

    lines = [f"# {REPORT_TITLES.get(report_type, 'Report')}", ""]
    lines.append("DEMO ENVIRONMENT — DATA IS SIMULATED" if any(i.is_demo for i in incidents) else "")
    lines.append("")

    lines.append("## VERIFIED FACTS")
    lines.append(f"- Total incidents in scope: {len(incidents)}")
    lines.append(f"- Human-verified incidents: {len(verified)}")
    lines.append(f"- Unverified / pending reports: {len(unverified)}")
    lines.append(f"- Open investigations: {len(open_investigations)}")
    lines.append(f"- Incidents affecting a water body or protected area: {len(environmental)}")
    lines.append("")

    lines.append("## RECENT DEVELOPMENTS")
    for i in recent:
        lines.append(f"- `{i.reference_number}` — {i.title} — status: {i.status.value} — {i.created_at.date().isoformat()}")
    lines.append("")

    lines.append("## AI-GENERATED INTERPRETATION")
    lines.append(
        f"- {len(high_risk)} location(s) carry an AI-generated operational risk score of 61+ "
        "(High/Critical). This reflects investigation priority, not confirmed illegal activity — "
        "all require field verification before any public statement names a location."
    )
    if high_risk:
        lines.append("- Highest-priority locations for field verification:")
        for i in sorted(high_risk, key=lambda x: x.risk_score or 0, reverse=True)[:5]:
            lines.append(f"  - `{i.reference_number}` — risk score {i.risk_score} (AI-generated, requires verification)")
    lines.append("")

    lines.append("## DATA GAPS")
    if not verified:
        lines.append("- No incidents in this scope have completed human field verification yet.")
    else:
        lines.append("- None noted for this scope.")
    lines.append("")

    lines.append("## SOURCE RECORDS")
    lines.append(", ".join(i.reference_number for i in incidents))

    return GeneratedReport(
        title=REPORT_TITLES.get(report_type, "Report"),
        content_markdown="\n".join(lines),
        source_incident_ids=[str(i.id) for i in incidents],
    )
