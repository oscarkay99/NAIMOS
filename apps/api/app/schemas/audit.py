import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class AuditLogOut(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str | None
    entity_id: str | None
    previous_value: str | None
    new_value: str | None
    reason: str | None
    created_at: datetime
