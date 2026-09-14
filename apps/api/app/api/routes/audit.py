from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("")
def list_audit_logs(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit:view")),
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
) -> list[dict]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)

    return [
        {
            "id": str(row.id), "user_id": str(row.user_id) if row.user_id else None, "action": row.action,
            "entity_type": row.entity_type, "entity_id": row.entity_id, "previous_value": row.previous_value,
            "new_value": row.new_value, "reason": row.reason, "created_at": row.created_at.isoformat(),
        }
        for row in db.execute(stmt).scalars().all()
    ]
