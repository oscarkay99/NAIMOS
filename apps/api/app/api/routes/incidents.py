import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.enums import IncidentStatus, VerificationStatus
from app.models.incident import Incident, IncidentStatusHistory
from app.models.report import Report, ReportSource
from app.models.user import User
from app.schemas.incident import (
    IncidentCreate,
    IncidentDetailOut,
    IncidentOut,
    IncidentUpdate,
    StatusChangeRequest,
)
from app.schemas.report import ReportOut
from app.services.audit import log_action
from app.services.geospatial.queries import district_for_point
from app.services.reports.generator import generate_preliminary_report
from app.services.risk.engine import persist_risk_score

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def _generate_reference_number() -> str:
    year = datetime.now(timezone.utc).year
    return f"NAIMOS-{year}-{str(uuid.uuid4())[:6].upper()}"


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("incident:read")),
    region_id: uuid.UUID | None = None,
    district_id: uuid.UUID | None = None,
    status_filter: IncidentStatus | None = Query(None, alias="status"),
    verification_status: VerificationStatus | None = None,
    min_risk: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
) -> list[Incident]:
    stmt = select(Incident)
    if region_id:
        stmt = stmt.where(Incident.region_id == region_id)
    if district_id:
        stmt = stmt.where(Incident.district_id == district_id)
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)
    if verification_status:
        stmt = stmt.where(Incident.verification_status == verification_status)
    if min_risk is not None:
        stmt = stmt.where(Incident.risk_score >= min_risk)
    if date_from:
        stmt = stmt.where(Incident.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Incident.created_at <= date_to)
    if search:
        like = f"%{search}%"
        stmt = stmt.where((Incident.title.ilike(like)) | (Incident.reference_number.ilike(like)))

    stmt = stmt.order_by(Incident.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=IncidentDetailOut, status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: IncidentCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("incident:create")),
) -> Incident:
    region_id = payload.region_id
    district_id = payload.district_id
    if region_id is None or district_id is None:
        located = district_for_point(db, payload.latitude, payload.longitude)
        if located:
            district_id = district_id or located["id"]
            region_id = region_id or located["region_id"]

    incident = Incident(
        reference_number=_generate_reference_number(),
        title=payload.title,
        description=payload.description,
        location=from_shape(Point(payload.longitude, payload.latitude), srid=4326),
        latitude=payload.latitude,
        longitude=payload.longitude,
        region_id=region_id,
        district_id=district_id,
        community_id=payload.community_id,
        incident_type=payload.incident_type,
        environmental_impact=payload.environmental_impact,
        water_body_affected=payload.water_body_affected,
        protected_area_affected=payload.protected_area_affected,
        equipment_observed=payload.equipment_observed,
        estimated_people_present=payload.estimated_people_present,
        priority=payload.priority,
        classification=payload.classification,
        created_by=user.id,
    )
    db.add(incident)
    db.flush()

    db.add(IncidentStatusHistory(
        incident_id=incident.id,
        previous_status=None,
        new_status=IncidentStatus.NEW,
        changed_by=user.id,
        reason="Incident created",
        changed_at=datetime.now(timezone.utc),
    ))

    persist_risk_score(db, incident)

    log_action(
        db, user_id=user.id, action="incident.created", entity_type="incident", entity_id=str(incident.id),
        new_value=incident.title, ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(incident)
    return incident


@router.get("/{incident_id}", response_model=IncidentDetailOut)
def get_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("incident:read")),
) -> Incident:
    incident = db.execute(
        select(Incident).options(selectinload(Incident.status_history)).where(Incident.id == incident_id)
    ).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")
    return incident


@router.patch("/{incident_id}", response_model=IncidentDetailOut)
def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("incident:update")),
) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(incident, field, value)

    log_action(
        db, user_id=user.id, action="incident.updated", entity_type="incident", entity_id=str(incident.id),
        new_value=str(changes), ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(incident)
    return incident


@router.post("/{incident_id}/status", response_model=IncidentDetailOut)
def change_status(
    incident_id: uuid.UUID,
    payload: StatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("incident:change_status")),
) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")

    previous_status = incident.status
    incident.status = payload.new_status
    if payload.new_status == IncidentStatus.VERIFIED:
        incident.verification_status = VerificationStatus.VERIFIED
    elif payload.new_status == IncidentStatus.UNVERIFIED:
        incident.verification_status = VerificationStatus.REJECTED

    db.add(IncidentStatusHistory(
        incident_id=incident.id,
        previous_status=previous_status,
        new_status=payload.new_status,
        changed_by=user.id,
        reason=payload.reason,
        changed_at=datetime.now(timezone.utc),
    ))

    log_action(
        db, user_id=user.id, action="incident.status_changed", entity_type="incident", entity_id=str(incident.id),
        previous_value=previous_status.value, new_value=payload.new_status.value, reason=payload.reason,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(incident)
    return incident


@router.post("/{incident_id}/preliminary-report", response_model=ReportOut)
def generate_incident_preliminary_report(
    incident_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("report:generate_preliminary")),
) -> ReportOut:
    """'The AI can then generate the official preliminary report' - the field
    officer's capture (location, equipment, evidence, voice statement) is
    assembled into one structured document. See services/reports/generator.py
    for exactly what's database-sourced vs. AI-assembled."""
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")

    generated = generate_preliminary_report(db, incident)

    report = Report(
        report_type="preliminary_field_report",
        title=generated.title,
        filters={"incident_id": str(incident_id)},
        content_markdown=generated.content_markdown,
        generated_by=user.id,
        model_name="naimos-report-assembler",
        model_version="0.1.0-demo",
    )
    db.add(report)
    db.flush()
    for source_id in generated.source_incident_ids:
        db.add(ReportSource(report_id=report.id, incident_id=source_id))

    log_action(
        db, user_id=user.id, action="report.preliminary_generated", entity_type="incident", entity_id=str(incident.id),
        new_value=report.title, ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(report)

    return ReportOut(
        id=report.id, report_type=report.report_type, title=report.title, content_markdown=report.content_markdown,
        model_name=report.model_name, model_version=report.model_version,
        source_incident_ids=[s.incident_id for s in report.sources], created_at=report.created_at,
    )


@router.get("/{incident_id}/preliminary-report", response_model=ReportOut | None)
def get_incident_preliminary_report(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("report:generate_preliminary")),
) -> ReportOut | None:
    """Returns the most recently generated preliminary report for this
    incident, if any, without generating a new one."""
    report = db.execute(
        select(Report)
        .join(ReportSource, ReportSource.report_id == Report.id)
        .where(ReportSource.incident_id == incident_id, Report.report_type == "preliminary_field_report")
        .order_by(Report.created_at.desc())
    ).scalars().first()
    if report is None:
        return None
    return ReportOut(
        id=report.id, report_type=report.report_type, title=report.title, content_markdown=report.content_markdown,
        model_name=report.model_name, model_version=report.model_version,
        source_incident_ids=[s.incident_id for s in report.sources], created_at=report.created_at,
    )
