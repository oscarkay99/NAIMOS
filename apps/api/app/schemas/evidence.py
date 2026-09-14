import uuid
from datetime import datetime

from app.models.enums import EvidenceFileType, VerificationStatus
from app.schemas.common import ORMModel


class EvidenceOut(ORMModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    uploaded_by: uuid.UUID
    file_type: EvidenceFileType
    original_filename: str
    file_hash: str
    file_size_bytes: int
    captured_at: datetime | None
    description: str | None
    ai_analysis: dict | None
    verification_status: VerificationStatus
    current_version: int
    created_at: datetime


class ObjectDetectionResult(ORMModel):
    label: str
    confidence: float


class ImageAnalysisOut(ORMModel):
    """AI image analysis result (section 12) - an observation aid only, never
    legal proof, and never facial/biometric identification."""

    detections: list[ObjectDetectionResult]
    model_name: str
    model_version: str
    disclaimer: str = (
        "AI image analysis is an observation aid, not legal proof. "
        "No facial recognition or biometric identification is performed."
    )
