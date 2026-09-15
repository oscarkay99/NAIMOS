import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db, get_readonly_db
from app.models.ai import AIDetection, AIQuery
from app.models.enums import AIReviewStatus
from app.models.evidence import Evidence
from app.models.user import User
from app.schemas.ai import AIDetectionOut, AIFeedbackRequest, AssistantQueryResponse
from app.schemas.evidence import ImageAnalysisOut, ObjectDetectionResult
from app.schemas.ai import AssistantQueryRequest
from app.services.ai.llm_provider import get_llm_provider
from app.services.ai.nl_query import detect_intent, format_answer, run_intent
from app.services.audit import log_action
from app.services.storage.local_storage import get_storage_provider

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/query", response_model=AssistantQueryResponse)
def assistant_query(
    payload: AssistantQueryRequest,
    request: Request,
    db: Session = Depends(get_db),
    readonly_db: Session = Depends(get_readonly_db),
    user: User = Depends(require_permission("ai:query")),
) -> AssistantQueryResponse:
    """NAIMOS Intelligence Assistant (section 19/20). Runs ONLY allowlisted,
    parametrized queries against the read-only DB role - never free-form
    AI-generated SQL - and never answers beyond what the database contains."""
    start = time.monotonic()
    intent = detect_intent(payload.question)

    if intent is None:
        answer = (
            "I can only answer from verified database records using a fixed set of "
            "supported questions (e.g. districts with most verified incidents, "
            "emerging hotspots, high-risk unverified areas, incidents near water "
            "bodies, region summaries, incidents open more than N days, or a "
            "briefing for today). I don't recognize this question - insufficient "
            "verified data to answer safely."
        )
        row_count = 0
        data: list[dict] = []
        insufficient = True
    else:
        outcome = run_intent(readonly_db, intent, payload.question)
        answer = format_answer(outcome)
        data = outcome.rows
        row_count = len(outcome.rows)
        insufficient = row_count == 0

    duration_ms = int((time.monotonic() - start) * 1000)
    llm = get_llm_provider()

    log = AIQuery(
        user_id=user.id, question=payload.question, detected_intent=intent or "unrecognized",
        generated_query=None, result_summary=answer[:2000], model_name=llm.name, model_version=llm.version,
        row_count=row_count, duration_ms=duration_ms, created_at=datetime.now(timezone.utc),
    )
    db.add(log)
    log_action(
        db, user_id=user.id, action="ai.query", entity_type="ai_query", entity_id=str(log.id),
        new_value=payload.question, metadata={"intent": intent, "row_count": row_count},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return AssistantQueryResponse(
        question=payload.question, detected_intent=intent or "unrecognized", answer=answer, data=data,
        row_count=row_count, model_name=llm.name, model_version=llm.version, insufficient_data=insufficient,
    )


@router.post("/analyze-image/{evidence_id}", response_model=ImageAnalysisOut)
def analyze_image(
    evidence_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("ai:analyze_image")),
) -> ImageAnalysisOut:
    """Section 12 - object-detection aid only. Never facial recognition, never
    treated as legal proof."""
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")

    storage = get_storage_provider()
    llm = get_llm_provider()
    absolute_path = str(storage.absolute_path(evidence.file_path))
    detections = llm.analyze_image(absolute_path)

    result = ImageAnalysisOut(
        detections=[
            ObjectDetectionResult(label=d.label, confidence=d.confidence, count=d.count) for d in detections
        ],
        model_name=llm.name, model_version=llm.version,
    )
    evidence.ai_analysis = result.model_dump()

    log_action(
        db, user_id=user.id, action="ai.image_analysis", entity_type="evidence", entity_id=str(evidence.id),
        new_value=str(detections), ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return result


@router.get("/detections", response_model=list[AIDetectionOut])
def list_detections(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("risk:view")),
) -> list[AIDetection]:
    return list(db.execute(select(AIDetection).order_by(AIDetection.observation_date.desc())).scalars().all())


@router.post("/detections/{detection_id}/feedback", response_model=AIDetectionOut)
def submit_feedback(
    detection_id: uuid.UUID,
    payload: AIFeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("ai:analyze_image")),
) -> AIDetection:
    """Human feedback loop (section 34) - an authorized user marks an AI
    detection useful/not useful/confirmed/rejected/needs review."""
    detection = db.get(AIDetection, detection_id)
    if detection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Detection not found")

    try:
        new_status = AIReviewStatus(payload.review_status)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid review_status")

    previous = detection.review_status
    detection.review_status = new_status
    detection.reviewed_by = user.id
    detection.reviewed_at = datetime.now(timezone.utc)

    log_action(
        db, user_id=user.id, action="ai.detection_feedback", entity_type="ai_detection", entity_id=str(detection.id),
        previous_value=previous.value, new_value=new_status.value, reason=payload.note,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(detection)
    return detection
