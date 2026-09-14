import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.enums import EvidenceFileType
from app.models.evidence import Evidence, EvidenceVersion
from app.models.user import User
from app.schemas.evidence import EvidenceOut
from app.services.audit import log_action
from app.services.storage.local_storage import get_storage_provider

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

_EXT_TYPE_MAP = {
    ".jpg": EvidenceFileType.IMAGE, ".jpeg": EvidenceFileType.IMAGE, ".png": EvidenceFileType.IMAGE,
    ".mp4": EvidenceFileType.VIDEO, ".mov": EvidenceFileType.VIDEO,
    ".mp3": EvidenceFileType.AUDIO, ".wav": EvidenceFileType.AUDIO, ".m4a": EvidenceFileType.AUDIO,
    ".pdf": EvidenceFileType.DOCUMENT, ".docx": EvidenceFileType.DOCUMENT,
}


def _infer_file_type(filename: str) -> EvidenceFileType:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _EXT_TYPE_MAP.get(ext, EvidenceFileType.DOCUMENT)


@router.post("", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    request: Request,
    incident_id: uuid.UUID = Form(...),
    description: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("evidence:upload")),
) -> Evidence:
    content = await file.read()
    storage = get_storage_provider()
    relative_path, file_hash, size = storage.save(f"incidents/{incident_id}", file.filename or "upload.bin", content)

    location = None
    if latitude is not None and longitude is not None:
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point
        location = from_shape(Point(longitude, latitude), srid=4326)

    evidence = Evidence(
        incident_id=incident_id,
        uploaded_by=user.id,
        file_type=_infer_file_type(file.filename or ""),
        original_filename=file.filename or "upload.bin",
        file_path=relative_path,
        file_hash=file_hash,
        file_size_bytes=size,
        location=location,
        captured_at=datetime.now(timezone.utc),
        description=description,
    )
    db.add(evidence)
    db.flush()
    db.add(EvidenceVersion(
        evidence_id=evidence.id, version_number=1, file_path=relative_path, file_hash=file_hash,
        uploaded_by=user.id, reason="Initial upload",
    ))

    log_action(
        db, user_id=user.id, action="evidence.uploaded", entity_type="evidence", entity_id=str(evidence.id),
        new_value=evidence.original_filename, metadata={"incident_id": str(incident_id), "sha256": file_hash},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/incident/{incident_id}", response_model=list[EvidenceOut])
def list_evidence_for_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("evidence:read")),
) -> list[Evidence]:
    return list(db.execute(select(Evidence).where(Evidence.incident_id == incident_id).order_by(Evidence.created_at.desc())).scalars().all())


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("evidence:read")),
) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")
    return evidence


@router.get("/{evidence_id}/download")
def download_evidence(
    evidence_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("evidence:read")),
) -> Response:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")

    storage = get_storage_provider()
    content = storage.read(evidence.file_path)

    log_action(
        db, user_id=user.id, action="evidence.downloaded", entity_type="evidence", entity_id=str(evidence.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return Response(content=content, media_type="application/octet-stream", headers={
        "Content-Disposition": f'attachment; filename="{evidence.original_filename}"'
    })
