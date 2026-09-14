from app.db.base import Base  # noqa: F401

# Import every model module so SQLAlchemy's declarative registry and
# Alembic's autogenerate both see the full schema.
from app.models import (  # noqa: F401
    ai,
    audit,
    evidence,
    field_report,
    geo,
    incident,
    investigation,
    notification,
    report,
    system,
    user,
)
