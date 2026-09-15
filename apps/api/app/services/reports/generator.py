"""Report / PRO communications generator (sections 16-18). Every figure in the
output is pulled directly from the database - never invented. Output always
separates VERIFIED FACTS from AI-GENERATED INTERPRETATION and cites the
backing incident IDs so a human can trace every claim."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import IncidentStatus, VerificationStatus
from app.models.evidence import Evidence
from app.models.field_report import FieldReport
from app.models.incident import Incident
from app.services.geospatial.queries import nearest_protected_area, nearest_water_body

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
                "from an empty result set - figures are never fabricated."
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
    lines.append("DEMO ENVIRONMENT - DATA IS SIMULATED" if any(i.is_demo for i in incidents) else "")
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
        lines.append(f"- `{i.reference_number}` - {i.title} - status: {i.status.value} - {i.created_at.date().isoformat()}")
    lines.append("")

    lines.append("## AI-GENERATED INTERPRETATION")
    lines.append(
        f"- {len(high_risk)} location(s) carry an AI-generated operational risk score of 61+ "
        "(High/Critical). This reflects investigation priority, not confirmed illegal activity - "
        "all require field verification before any public statement names a location."
    )
    if high_risk:
        lines.append("- Highest-priority locations for field verification:")
        for i in sorted(high_risk, key=lambda x: x.risk_score or 0, reverse=True)[:5]:
            lines.append(f"  - `{i.reference_number}` - risk score {i.risk_score} (AI-generated, requires verification)")
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


def _recommended_classification(incident: Incident) -> str:
    """A simple, transparent rule - not an LLM guess - so the recommendation
    is always traceable to the same fields shown elsewhere on the record."""
    score = incident.risk_score or 0
    if score >= 61:
        urgency = "Priority field verification recommended"
    elif score >= 41:
        urgency = "Field verification recommended"
    else:
        urgency = "Continue monitoring; verify as resources allow"

    type_label = incident.incident_type.value.replace("_", " ").title()
    return f"{type_label} - {urgency} (AI-suggested classification, requires supervisor confirmation)"


def generate_preliminary_report(db: Session, incident: Incident) -> GeneratedReport:
    """The 'AI writes the preliminary report' feature for a single field
    incident: assembles everything already on record (location, equipment,
    environmental impact, evidence, officer statement) into one structured
    document. Every fact comes straight from the database - the only
    AI-authored parts are the recommended classification (a transparent
    rule, see above) and, if present, the voice-to-report transcript, which
    is itself officer-reviewed and approved before it ever reaches here."""
    water = nearest_water_body(db, incident.latitude, incident.longitude)
    protected = nearest_protected_area(db, incident.latitude, incident.longitude)

    evidence_items = list(
        db.execute(select(Evidence).where(Evidence.incident_id == incident.id).order_by(Evidence.created_at)).scalars().all()
    )
    field_report = db.execute(
        select(FieldReport)
        .where(FieldReport.incident_id == incident.id, FieldReport.officer_approved.is_(True))
        .order_by(FieldReport.created_at.desc())
    ).scalars().first()

    lines = [f"# Incident #{incident.reference_number} - Preliminary Field Report", ""]
    if incident.is_demo:
        lines.append("DEMO ENVIRONMENT - DATA IS SIMULATED")
        lines.append("")

    lines.append("## OFFICER-REPORTED FACTS")
    lines.append(f"- **Title:** {incident.title}")
    lines.append(f"- **Location:** {incident.latitude:.5f}, {incident.longitude:.5f}")
    lines.append(f"- **Date/time reported:** {incident.created_at.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"- **Incident type:** {incident.incident_type.value.replace('_', ' ').title()}")
    lines.append(f"- **Equipment observed:** {incident.equipment_observed or 'Not recorded'}")
    lines.append(
        f"- **Estimated number of persons present:** "
        f"{incident.estimated_people_present if incident.estimated_people_present is not None else 'Not recorded'}"
    )
    lines.append(f"- **Environmental impact noted:** {incident.environmental_impact or 'Not recorded'}")
    lines.append("")

    lines.append("## ENVIRONMENTAL PROXIMITY (AI-computed from GPS coordinates)")
    if water:
        dist_km = round(water["distance_m"] / 1000, 2)
        lines.append(f"- River/water body affected: {'Yes' if incident.water_body_affected else 'No'} - nearest is {water['name']}, {dist_km} km away")
    else:
        lines.append(f"- River/water body affected: {'Yes' if incident.water_body_affected else 'No'}")
    if protected:
        dist_km = round(protected["distance_m"] / 1000, 2)
        lines.append(f"- Forest/protected area affected: {'Yes' if incident.protected_area_affected else 'No'} - nearest is {protected['name']}, {dist_km} km away")
    else:
        lines.append(f"- Forest/protected area affected: {'Yes' if incident.protected_area_affected else 'No'}")
    lines.append("")

    lines.append("## EVIDENCE")
    if evidence_items:
        for ev in evidence_items:
            ai_note = ""
            if ev.ai_analysis and ev.ai_analysis.get("detections"):
                labels = ", ".join(f"{d['label']} ({round(d['confidence']*100)}%)" for d in ev.ai_analysis["detections"])
                ai_note = f" - AI-assisted observation: {labels} (not legal proof, requires verification)"
            lines.append(f"- {ev.file_type.value.title()}: `{ev.original_filename}`{ai_note}")
    else:
        lines.append("- No evidence attached yet.")
    lines.append("")

    lines.append("## OFFICER STATEMENT")
    if field_report and field_report.narrative:
        lines.append(f"> {field_report.narrative}")
        lines.append("")
        lines.append("*(Voice-recorded statement, transcribed by AI and reviewed/approved by the reporting officer.)*")
    elif incident.description:
        lines.append(f"> {incident.description}")
    else:
        lines.append("No officer narrative recorded.")
    lines.append("")

    lines.append("## RECOMMENDED CLASSIFICATION")
    lines.append(f"- {_recommended_classification(incident)}")
    lines.append("")
    lines.append(
        "*This preliminary report is AI-assembled from verified field-officer input and database records. "
        "It is not a confirmation of illegal activity and requires supervisor/analyst review before action.*"
    )

    return GeneratedReport(
        title=f"Preliminary Field Report - {incident.reference_number}",
        content_markdown="\n".join(lines),
        source_incident_ids=[str(incident.id)],
    )
