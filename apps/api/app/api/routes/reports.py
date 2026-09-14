from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.report import Report, ReportSource
from app.models.user import User
from app.schemas.report import ReportGenerateRequest, ReportOut
from app.services.ai.llm_provider import get_llm_provider
from app.services.audit import log_action
from app.services.reports.generator import generate_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/generate", response_model=ReportOut)
def generate(
    payload: ReportGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("report:generate")),
) -> ReportOut:
    generated = generate_report(
        db, payload.report_type, payload.region_id, payload.district_id, payload.date_from, payload.date_to
    )
    llm = get_llm_provider()

    report = Report(
        report_type=payload.report_type,
        title=generated.title,
        filters=payload.model_dump(mode="json", exclude={"report_type"}),
        content_markdown=generated.content_markdown,
        generated_by=user.id,
        model_name=llm.name,
        model_version=llm.version,
    )
    db.add(report)
    db.flush()
    for incident_id in generated.source_incident_ids:
        db.add(ReportSource(report_id=report.id, incident_id=incident_id))

    log_action(
        db, user_id=user.id, action="report.generated", entity_type="report", entity_id=str(report.id),
        new_value=payload.report_type, metadata={"source_count": len(generated.source_incident_ids)},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(report)

    return ReportOut(
        id=report.id, report_type=report.report_type, title=report.title, content_markdown=report.content_markdown,
        model_name=report.model_name, model_version=report.model_version,
        source_incident_ids=[s.incident_id for s in report.sources], created_at=report.created_at,
    )
