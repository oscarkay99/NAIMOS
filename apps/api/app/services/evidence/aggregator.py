"""Evidence Intelligence (section 12/57-ish of the spec): runs AI analysis
across every un-analyzed image in an incident's evidence, then consolidates
the per-file detections into one operational summary - "2 excavators, 1
mining pit" instead of forcing an officer to read 30 separate results.

Aggregation is deliberately conservative: for a countable class (e.g.
"Excavator"), the reported quantity is the MAXIMUM seen in any single photo,
not the sum across photos - summing would risk claiming the same excavator
was counted twice just because it appeared in two photos from different
angles. This is stated explicitly in the generated report's disclaimer.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import EvidenceFileType
from app.models.evidence import Evidence
from app.models.incident import Incident
from app.services.ai.llm_provider import get_llm_provider
from app.services.storage.local_storage import get_storage_provider

_LABEL_PREFIX = {
    EvidenceFileType.IMAGE: "PHOTO",
    EvidenceFileType.VIDEO: "VIDEO",
    EvidenceFileType.AUDIO: "AUDIO",
    EvidenceFileType.DOCUMENT: "DOC",
}


@dataclass
class ConsolidatedDetection:
    label: str
    max_count: int | None  # None for presence-only classes
    seen_in_items: int
    max_confidence: float


@dataclass
class EvidenceFileEntry:
    index_label: str  # e.g. "PHOTO-001"
    original_filename: str
    file_type: str
    primary_label: str | None
    analyzed: bool


@dataclass
class EvidencePackageData:
    consolidated: list[ConsolidatedDetection]
    files: list[EvidenceFileEntry]
    newly_analyzed_count: int
    total_evidence_count: int


def build_evidence_package(db: Session, incident: Incident) -> EvidencePackageData:
    evidence_items = list(
        db.execute(
            select(Evidence).where(Evidence.incident_id == incident.id).order_by(Evidence.created_at)
        ).scalars().all()
    )

    llm = get_llm_provider()
    storage = get_storage_provider()
    newly_analyzed = 0

    # Run AI analysis on any un-analyzed image that hasn't been looked at yet -
    # "the AI processes everything" rather than requiring one click per file.
    for ev in evidence_items:
        if ev.file_type == EvidenceFileType.IMAGE and not ev.ai_analysis:
            absolute_path = str(storage.absolute_path(ev.file_path))
            detections = llm.analyze_image(absolute_path)
            ev.ai_analysis = {
                "detections": [{"label": d.label, "confidence": d.confidence, "count": d.count} for d in detections],
                "model_name": llm.name,
                "model_version": llm.version,
            }
            newly_analyzed += 1
    db.flush()

    # Consolidate across all analyzed items.
    by_label: dict[str, ConsolidatedDetection] = {}
    for ev in evidence_items:
        if not ev.ai_analysis:
            continue
        for d in ev.ai_analysis.get("detections", []):
            label = d["label"]
            confidence = d["confidence"]
            count = d.get("count")
            existing = by_label.get(label)
            if existing is None:
                by_label[label] = ConsolidatedDetection(
                    label=label, max_count=count, seen_in_items=1, max_confidence=confidence,
                )
            else:
                existing.seen_in_items += 1
                existing.max_confidence = max(existing.max_confidence, confidence)
                if count is not None:
                    existing.max_count = max(existing.max_count or 0, count)

    consolidated = sorted(by_label.values(), key=lambda d: d.max_confidence, reverse=True)

    # Build the PHOTO-001 / VIDEO-001 style index, numbered per file type.
    counters: dict[EvidenceFileType, int] = {}
    files: list[EvidenceFileEntry] = []
    for ev in evidence_items:
        counters[ev.file_type] = counters.get(ev.file_type, 0) + 1
        prefix = _LABEL_PREFIX.get(ev.file_type, "FILE")
        index_label = f"{prefix}-{counters[ev.file_type]:03d}"

        primary_label = None
        if ev.ai_analysis and ev.ai_analysis.get("detections"):
            top = max(ev.ai_analysis["detections"], key=lambda d: d["confidence"])
            primary_label = top["label"]

        files.append(EvidenceFileEntry(
            index_label=index_label,
            original_filename=ev.original_filename,
            file_type=ev.file_type.value,
            primary_label=primary_label,
            analyzed=bool(ev.ai_analysis),
        ))

    return EvidencePackageData(
        consolidated=consolidated,
        files=files,
        newly_analyzed_count=newly_analyzed,
        total_evidence_count=len(evidence_items),
    )
