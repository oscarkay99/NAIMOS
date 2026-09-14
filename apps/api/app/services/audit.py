import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_action(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    previous_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Writes an audit record in the same DB transaction as the action it
    describes (section 25). Callers commit; this only adds+flushes so the
    generated id/created_at are available immediately if needed."""

    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_value=previous_value,
        new_value=new_value,
        reason=reason,
        metadata_json=metadata,
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
    return entry
