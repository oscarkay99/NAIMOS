import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.field_report import FieldReport
from app.models.user import User
from app.schemas.field_report import (
    FieldReportCreate,
    FieldReportOut,
    VoiceExtraction,
    VoiceReportApprove,
    VoiceReportTranscribeOut,
)
from app.services.ai.llm_provider import get_llm_provider
from app.services.ai.voice_extraction import extract_structured
from app.services.audit import log_action
from app.services.storage.local_storage import get_storage_provider

router = APIRouter(prefix="/api/field-reports", tags=["field-reports"])


@router.post("", response_model=FieldReportOut, status_code=status.HTTP_201_CREATED)
def create_field_report(
    payload: FieldReportCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("field_report:create")),
) -> FieldReport:
    report = FieldReport(
        incident_id=payload.incident_id,
        officer_id=user.id,
        location=from_shape(Point(payload.longitude, payload.latitude), srid=4326),
        narrative=payload.narrative,
        officer_approved=True,
        officer_approved_at=datetime.now(timezone.utc),
        captured_offline=payload.captured_offline,
        synced_at=datetime.now(timezone.utc) if payload.captured_offline else None,
    )
    db.add(report)
    log_action(
        db, user_id=user.id, action="field_report.created", entity_type="field_report", entity_id=None,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(report)
    return _to_out(report)


@router.post("/voice", response_model=VoiceReportTranscribeOut)
async def submit_voice_report(
    request: Request,
    file: UploadFile = File(...),
    incident_id: uuid.UUID | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("field_report:create")),
) -> VoiceReportTranscribeOut:
    """Section 10 - voice-to-report. The original audio is preserved verbatim;
    the transcript and extraction are AI-generated DRAFTS the officer must
    review and approve via /voice/approve before they become part of the record."""
    content = await file.read()
    storage = get_storage_provider()
    relative_path, _hash, _size = storage.save("voice-reports", file.filename or "voice.wav", content)

    llm = get_llm_provider()
    transcript = llm.transcribe_audio(relative_path)
    extraction = extract_structured(transcript)

    report = FieldReport(
        incident_id=incident_id,
        officer_id=user.id,
        original_audio_path=relative_path,
        transcript=transcript,
        ai_extraction=extraction.model_dump(),
        officer_approved=False,
    )
    db.add(report)

    log_action(
        db, user_id=user.id, action="field_report.voice_transcribed", entity_type="field_report", entity_id=None,
        new_value=transcript, ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(report)

    return VoiceReportTranscribeOut(
        field_report_id=report.id, transcript=transcript, extraction=extraction,
        model_name=llm.name, model_version=llm.version,
    )


@router.post("/voice/approve", response_model=FieldReportOut)
def approve_voice_report(
    payload: VoiceReportApprove,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("field_report:create")),
) -> FieldReport:
    """The officer confirms (optionally edits) the AI draft. Original audio and
    the original AI transcript/extraction are never overwritten - only the
    officer-approved fields are updated, and both remain queryable via the
    field_reports row for audit purposes."""
    report = db.get(FieldReport, payload.field_report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Field report not found")
    if report.officer_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the submitting officer can approve this report")

    if payload.edited_transcript is not None:
        report.narrative = payload.edited_transcript
    else:
        report.narrative = report.transcript
    # report.transcript is left untouched - it's the original AI transcript
    # of the recording and is never overwritten (section 10); narrative is
    # the officer-approved version the rest of the app reads from.

    if payload.edited_extraction is not None:
        report.ai_extraction = payload.edited_extraction.model_dump()

    if payload.incident_id is not None:
        report.incident_id = payload.incident_id

    report.officer_approved = True
    report.officer_approved_at = datetime.now(timezone.utc)

    log_action(
        db, user_id=user.id, action="field_report.voice_approved", entity_type="field_report",
        entity_id=str(report.id), ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(report)
    return _to_out(report)


def _to_out(report: FieldReport) -> FieldReportOut:
    from geoalchemy2.shape import to_shape

    lat = lon = None
    if report.location is not None:
        point = to_shape(report.location)
        lat, lon = point.y, point.x
    return FieldReportOut(
        id=report.id, incident_id=report.incident_id, officer_id=report.officer_id,
        latitude=lat, longitude=lon, narrative=report.narrative, transcript=report.transcript,
        ai_extraction=report.ai_extraction, officer_approved=report.officer_approved,
        officer_approved_at=report.officer_approved_at, captured_offline=report.captured_offline,
        created_at=report.created_at,
    )
