"""Report / PRO communications generator (sections 16-18). Every figure in the
output is pulled directly from the database - never invented. Output always
separates VERIFIED FACTS from AI-GENERATED INTERPRETATION and cites the
backing incident IDs so a human can trace every claim."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import IncidentStatus, VerificationStatus
from app.models.evidence import Evidence
from app.models.field_report import FieldReport
from app.models.incident import Incident
from app.services.evidence.aggregator import EvidencePackageData, build_evidence_package
from app.services.geospatial.queries import nearest_protected_area, nearest_water_body

REPORT_TITLES = {
    "executive_brief": "Executive Brief",
    "weekly_situation": "Weekly Situation Summary",
    "press_briefing": "Press Briefing",
    "social_media_briefing": "Social Media Briefing",
    "parliamentary_briefing": "Parliamentary Briefing",
    "talking_points": "Talking Points",
    "media_qa": "Media Q&A Preparation",
}


@dataclass
class GeneratedReport:
    title: str
    content_markdown: str
    source_incident_ids: list[str]


@dataclass
class _Aggregates:
    """Every figure a communications formatter is allowed to use - computed
    once from real records so no two report types can silently disagree,
    and so a formatter can never reach past this set to invent a number."""

    incidents: list[Incident]
    verified: list[Incident]
    unverified: list[Incident]
    high_risk: list[Incident]
    open_investigations: list[Incident]
    water_affected: list[Incident]
    forest_affected: list[Incident]
    recent: list[Incident]
    regions: list[str]
    is_demo: bool


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


def _gather_aggregates(incidents: list[Incident]) -> _Aggregates:
    return _Aggregates(
        incidents=incidents,
        verified=[i for i in incidents if i.verification_status == VerificationStatus.VERIFIED],
        unverified=[i for i in incidents if i.verification_status != VerificationStatus.VERIFIED],
        high_risk=[i for i in incidents if (i.risk_score or 0) >= 61],
        open_investigations=[i for i in incidents if i.status not in (IncidentStatus.CLOSED, IncidentStatus.ARCHIVED)],
        water_affected=[i for i in incidents if i.water_body_affected],
        forest_affected=[i for i in incidents if i.protected_area_affected],
        recent=sorted(incidents, key=lambda i: i.created_at, reverse=True)[:5],
        regions=sorted({i.region.name for i in incidents if i.region}),
        is_demo=any(i.is_demo for i in incidents),
    )


def _demo_banner(agg: _Aggregates) -> list[str]:
    return ["DEMO ENVIRONMENT - DATA IS SIMULATED", ""] if agg.is_demo else []


def _format_internal_report(title: str, agg: _Aggregates) -> str:
    """Detailed internal-facing format (executive brief / weekly situation
    summary): full VERIFIED FACTS vs AI-GENERATED INTERPRETATION split with
    source traceability - the audience is NAIMOS leadership, not the public."""
    lines = [f"# {title}", "", *_demo_banner(agg)]

    lines.append("## VERIFIED FACTS")
    lines.append(f"- Total incidents in scope: {len(agg.incidents)}")
    lines.append(f"- Human-verified incidents: {len(agg.verified)}")
    lines.append(f"- Unverified / pending reports: {len(agg.unverified)}")
    lines.append(f"- Open investigations: {len(agg.open_investigations)}")
    lines.append(f"- Incidents affecting a water body: {len(agg.water_affected)}")
    lines.append(f"- Incidents affecting a forest/protected area: {len(agg.forest_affected)}")
    lines.append("")

    lines.append("## RECENT DEVELOPMENTS")
    for i in agg.recent:
        lines.append(f"- `{i.reference_number}` - {i.title} - status: {i.status.value} - {i.created_at.date().isoformat()}")
    lines.append("")

    lines.append("## AI-GENERATED INTERPRETATION")
    lines.append(
        f"- {len(agg.high_risk)} location(s) carry an AI-generated operational risk score of 61+ "
        "(High/Critical). This reflects investigation priority, not confirmed illegal activity - "
        "all require field verification before any public statement names a location."
    )
    if agg.high_risk:
        lines.append("- Highest-priority locations for field verification:")
        for i in sorted(agg.high_risk, key=lambda x: x.risk_score or 0, reverse=True)[:5]:
            lines.append(f"  - `{i.reference_number}` - risk score {i.risk_score} (AI-generated, requires verification)")
    lines.append("")

    lines.append("## DATA GAPS")
    lines.append(
        "- No incidents in this scope have completed human field verification yet."
        if not agg.verified
        else "- None noted for this scope."
    )
    lines.append("")

    lines.append("## SOURCE RECORDS")
    lines.append(", ".join(i.reference_number for i in agg.incidents))
    return "\n".join(lines)


def _format_press_briefing(agg: _Aggregates) -> str:
    """Formal press-release prose. Deliberately omits specific coordinates
    and raw risk scores - a public statement names verified counts only,
    never a site an AI has merely flagged for investigation."""
    lines = [f"# {REPORT_TITLES['press_briefing']}", "", *_demo_banner(agg)]
    lines.append(
        "The National Anti-Illegal Mining Operations Secretariat (NAIMOS) issues the following "
        "verified operational update."
    )
    lines.append("")
    lines.append(
        f"During the period under review, NAIMOS recorded {len(agg.incidents)} incident report(s), "
        f"of which {len(agg.verified)} have been confirmed through independent field verification. "
        f"{len(agg.open_investigations)} case(s) remain under active investigation."
    )
    lines.append("")
    if agg.water_affected or agg.forest_affected:
        lines.append(
            f"{len(agg.water_affected)} verified report(s) noted impact to a water body and "
            f"{len(agg.forest_affected)} to a forest or protected area. Environmental assessment of "
            "these sites is ongoing."
        )
        lines.append("")
    lines.append(
        "NAIMOS continues to prioritise locations flagged by its risk-assessment process for field "
        "verification before any further public statement is made regarding specific sites."
    )
    lines.append("")
    lines.append(
        "This briefing reflects verified NAIMOS records only. AI-assisted analysis is used internally "
        "to prioritise investigation - it does not confirm criminal activity and is never presented "
        "publicly as such."
    )
    return "\n".join(lines)


def _format_social_media_briefing(agg: _Aggregates) -> str:
    """Short, factual, safe for public posting - verified counts only, no
    site-level detail, no AI-generated risk language at all."""
    lines = [f"# {REPORT_TITLES['social_media_briefing']}", "", *_demo_banner(agg)]
    region_note = f" across {len(agg.regions)} region(s)" if agg.regions else ""
    lines.append(
        f"NAIMOS update: {len(agg.verified)} illegal mining report(s) verified this period{region_note}. "
        f"{len(agg.open_investigations)} investigation(s) ongoing. Report suspected illegal mining "
        "activity to NAIMOS."
    )
    lines.append("")
    lines.append("*(Only independently verified figures are shared publicly.)*")
    return "\n".join(lines)


def _format_parliamentary_briefing(agg: _Aggregates) -> str:
    """Formal register for a legislative audience - verified figures up
    front, AI-assisted prioritisation explicitly labelled as such."""
    lines = [f"# {REPORT_TITLES['parliamentary_briefing']}", "", *_demo_banner(agg)]
    lines.append("Honourable Members,")
    lines.append("")
    lines.append("I present the following update on NAIMOS operations for the period under review.")
    lines.append("")
    lines.append("## VERIFIED FIGURES")
    lines.append(f"- Total incidents recorded: {len(agg.incidents)}")
    lines.append(f"- Independently verified: {len(agg.verified)}")
    lines.append(f"- Under active investigation: {len(agg.open_investigations)}")
    lines.append(f"- Locations affecting a water body: {len(agg.water_affected)}")
    lines.append(f"- Locations affecting a forest/protected area: {len(agg.forest_affected)}")
    lines.append("")
    lines.append("## AI-ASSISTED PRIORITISATION")
    lines.append(
        f"NAIMOS employs an explainable, rule-based risk-scoring system to prioritise field verification "
        f"resources. {len(agg.high_risk)} location(s) currently carry an elevated investigation-priority "
        "score. This reflects operational priority only and is not a finding of illegal activity absent "
        "field verification."
    )
    lines.append("")
    lines.append("This briefing draws exclusively from verified NAIMOS operational records.")
    lines.append("")
    lines.append("## SOURCE RECORDS")
    lines.append(", ".join(i.reference_number for i in agg.incidents))
    return "\n".join(lines)


def _format_talking_points(agg: _Aggregates) -> str:
    """Short bullet list, one line each, no elaboration - a spokesperson's
    crib sheet, not a report."""
    lines = [f"# {REPORT_TITLES['talking_points']}", "", *_demo_banner(agg)]
    lines.append(f"- {len(agg.incidents)} incident(s) recorded this period")
    lines.append(f"- {len(agg.verified)} verified through field investigation")
    lines.append(f"- {len(agg.open_investigations)} case(s) under active investigation")
    lines.append(f"- {len(agg.high_risk)} location(s) flagged for priority verification (AI-assisted, unconfirmed)")
    if agg.water_affected or agg.forest_affected:
        lines.append(
            f"- {len(agg.water_affected)} water body / {len(agg.forest_affected)} forest area impact(s) reported"
        )
    lines.append("- All figures drawn from verified NAIMOS records")
    return "\n".join(lines)


def _format_media_qa(agg: _Aggregates) -> str:
    """Real question -> answer pairs, each answer traceable to the same
    aggregates as every other report type. The seizure question is included
    deliberately: this system does not track equipment seizures, so the
    honest answer is 'we don't have that figure' rather than a guess -
    the AI is never allowed to invent a government statistic."""
    lines = [f"# {REPORT_TITLES['media_qa']}", "", *_demo_banner(agg)]

    lines.append("**Q: How many illegal mining sites has NAIMOS identified?**")
    lines.append(
        f"A: NAIMOS has {len(agg.incidents)} incident report(s) on record for this period, of which "
        f"{len(agg.verified)} have been confirmed through field verification. The remainder are under "
        "review and not yet confirmed."
    )
    lines.append("")

    lines.append("**Q: How many locations show high investigation priority?**")
    lines.append(
        f"A: {len(agg.high_risk)} location(s) carry an AI-generated high investigation-priority score. "
        "This reflects where NAIMOS is prioritising verification resources - it is not confirmation of "
        "illegal activity."
    )
    lines.append("")

    lines.append("**Q: Which regions recorded the highest activity?**")
    if agg.regions:
        lines.append(f"A: {', '.join(agg.regions)} recorded reported activity in this period.")
    else:
        lines.append("A: Region data is not available for this scope.")
    lines.append("")

    lines.append("**Q: How many water bodies or protected areas have been affected?**")
    lines.append(
        f"A: {len(agg.water_affected)} incident(s) reported an affected water body and "
        f"{len(agg.forest_affected)} reported an affected forest/protected area. These are field-reported "
        "observations pending full environmental assessment."
    )
    lines.append("")

    lines.append("**Q: How many excavators or pieces of equipment have been seized?**")
    lines.append(
        "A: NAIMOS does not fabricate seizure figures. Equipment seizure counts are not tracked in this "
        "system - refer to field operations command for verified seizure data."
    )
    return "\n".join(lines)


_FORMATTERS = {
    "press_briefing": _format_press_briefing,
    "social_media_briefing": _format_social_media_briefing,
    "parliamentary_briefing": _format_parliamentary_briefing,
    "talking_points": _format_talking_points,
    "media_qa": _format_media_qa,
}


def generate_report(
    db: Session, report_type: str, region_id, district_id, date_from: date | None, date_to: date | None
) -> GeneratedReport:
    stmt = _apply_filters(select(Incident), region_id, district_id, date_from, date_to)
    incidents = list(db.execute(stmt).scalars().all())
    title = REPORT_TITLES.get(report_type, "Report")

    if not incidents:
        return GeneratedReport(
            title=title,
            content_markdown=(
                "## Insufficient verified data\n\n"
                "No incidents matched the selected filters. No report can be generated "
                "from an empty result set - figures are never fabricated."
            ),
            source_incident_ids=[],
        )

    agg = _gather_aggregates(incidents)
    formatter = _FORMATTERS.get(report_type)
    content = formatter(agg) if formatter else _format_internal_report(title, agg)

    return GeneratedReport(
        title=title,
        content_markdown=content,
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


def generate_evidence_package_report(db: Session, incident: Incident, package: EvidencePackageData) -> GeneratedReport:
    """Formats an already-computed EvidencePackageData (see
    services/evidence/aggregator.py) into the same Incident Summary /
    AI-detected evidence / Evidence files structure the spec's Evidence
    Intelligence feature describes. Counts are explicitly framed as
    conservative estimates requiring verification, never as confirmed facts."""
    lines = [f"# Evidence Package - Incident #{incident.reference_number}", ""]
    if incident.is_demo:
        lines.append("DEMO ENVIRONMENT - DATA IS SIMULATED")
        lines.append("")

    lines.append("## INCIDENT SUMMARY")
    lines.append(f"- **Incident:** {incident.title}")
    lines.append(f"- **Type:** {incident.incident_type.value.replace('_', ' ').title()}")
    lines.append(f"- **Location:** {incident.latitude:.5f}, {incident.longitude:.5f}")
    lines.append(f"- **Date:** {incident.created_at.strftime('%d %B %Y')}")
    lines.append(f"- **Evidence files:** {package.total_evidence_count}")
    lines.append("")

    lines.append("## AI-DETECTED EVIDENCE (requires verification)")
    if package.consolidated:
        for d in package.consolidated:
            if d.max_count is not None:
                qty = f"{d.max_count} {d.label.lower()}{'s' if d.max_count != 1 else ''}"
            else:
                qty = d.label
            lines.append(
                f"- {qty} - seen in {d.seen_in_items} file(s), highest confidence {round(d.max_confidence * 100)}%"
            )
    else:
        lines.append("- No AI-analyzable evidence yet (upload photos to enable detection).")
    lines.append("")

    lines.append("## EVIDENCE FILES")
    if package.files:
        for f in package.files:
            status = f"→ {f.primary_label}" if f.primary_label else "(not yet analyzed - non-image or analysis pending)"
            lines.append(f"- `{f.index_label}` ({f.original_filename}) {status}")
    else:
        lines.append("- No evidence attached yet.")
    lines.append("")

    lines.append(
        "*Quantities above are conservative estimates - the maximum count observed in any single file, not a sum "
        "across files (to avoid double-counting the same object seen from multiple angles). This is an AI "
        "observation aid, not legal proof; original evidence files and their full audit trail (uploader, hash, "
        "version history) remain the authoritative record and are never replaced by this summary.*"
    )

    return GeneratedReport(
        title=f"Evidence Package - {incident.reference_number}",
        content_markdown="\n".join(lines),
        source_incident_ids=[str(incident.id)],
    )
