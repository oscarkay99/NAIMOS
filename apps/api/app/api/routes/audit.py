from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogOut
from app.schemas.common import Page

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=Page[AuditLogOut])
def list_audit_logs(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit:view")),
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
) -> Page[AuditLogOut]:
    """Paginated: the audit log grows by one row on every sensitive action
    across the whole platform, so unlike most other lists in this app it has
    no natural size cap - a real `total` lets the UI show how much history
    exists beyond whatever fits in one page, instead of silently truncating."""
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)

    total = db.execute(select(func.count()).select_from(AuditLog).where(*filters)).scalar_one()

    stmt = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(stmt).scalars().all()

    return Page(items=[AuditLogOut.model_validate(row) for row in rows], total=total, limit=limit, offset=offset)
