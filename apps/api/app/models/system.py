import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
