import uuid

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk


class Region(Base, TimestampMixin):
    __tablename__ = "regions"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    capital: Mapped[str | None] = mapped_column(String(128), nullable=True)
    centroid: Mapped[str | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)

    districts: Mapped[list["District"]] = relationship(back_populates="region")


class District(Base, TimestampMixin):
    __tablename__ = "districts"

    id: Mapped[uuid.UUID] = uuid_pk()
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    capital: Mapped[str | None] = mapped_column(String(128), nullable=True)
    centroid: Mapped[str | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)

    region: Mapped["Region"] = relationship(back_populates="districts")
    communities: Mapped[list["Community"]] = relationship(back_populates="district")


class Community(Base, TimestampMixin):
    __tablename__ = "communities"

    id: Mapped[uuid.UUID] = uuid_pk()
    district_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)

    district: Mapped["District"] = relationship(back_populates="communities")


class WaterBody(Base, TimestampMixin):
    __tablename__ = "water_bodies"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    water_type: Mapped[str] = mapped_column(String(32), default="river")  # river | lake | reservoir
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProtectedArea(Base, TimestampMixin):
    __tablename__ = "protected_areas"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    area_type: Mapped[str] = mapped_column(String(32), default="protected")  # protected | national_park
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ForestReserve(Base, TimestampMixin):
    __tablename__ = "forest_reserves"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False), nullable=False)
    area_hectares: Mapped[float | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
