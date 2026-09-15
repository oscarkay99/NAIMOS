"""PostGIS-backed spatial lookups (section 54): nearest water body / protected
area, district containment, distance queries. All distances are computed with
geography casts so results are in real metres, not degrees."""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def nearest_water_body(db: Session, lat: float, lon: float) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id, name,
                   ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS distance_m
            FROM water_bodies
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            LIMIT 1
            """
        ),
        {"lat": lat, "lon": lon},
    ).mappings().first()
    return dict(row) if row else None


def nearest_protected_area(db: Session, lat: float, lon: float) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id, name,
                   ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS distance_m
            FROM protected_areas
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            LIMIT 1
            """
        ),
        {"lat": lat, "lon": lon},
    ).mappings().first()
    return dict(row) if row else None


def district_for_point(db: Session, lat: float, lon: float, max_distance_km: float = 50) -> dict | None:
    """Ghana district boundaries aren't loaded in this demo (no boundary
    polygons seeded) - falls back to nearest district centroid within range."""
    row = db.execute(
        text(
            """
            SELECT d.id, d.name, r.id AS region_id, r.name AS region_name,
                   ST_Distance(d.centroid::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS distance_m
            FROM districts d
            JOIN regions r ON r.id = d.region_id
            WHERE d.centroid IS NOT NULL
            ORDER BY d.centroid <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            LIMIT 1
            """
        ),
        {"lat": lat, "lon": lon},
    ).mappings().first()
    if row and row["distance_m"] <= max_distance_km * 1000:
        return dict(row)
    return None


def nearest_other_incident(db: Session, lat: float, lon: float, exclude_id: uuid.UUID | None = None) -> dict | None:
    """Nearest incident to a point, excluding a given incident itself -
    powers the 'previous mining activity N km away' predictive signal."""
    query = """
        SELECT id, reference_number,
               ST_Distance(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS distance_m
        FROM incidents
        WHERE 1=1
    """
    params: dict = {"lat": lat, "lon": lon}
    if exclude_id is not None:
        query += " AND id != :exclude_id"
        params["exclude_id"] = str(exclude_id)
    query += " ORDER BY location <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) LIMIT 1"
    row = db.execute(text(query), params).mappings().first()
    return dict(row) if row else None


def count_nearby_incidents(db: Session, lat: float, lon: float, radius_km: float, exclude_id: uuid.UUID | None = None) -> int:
    query = """
        SELECT COUNT(*) FROM incidents
        WHERE ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
    """
    params: dict = {"lat": lat, "lon": lon, "radius_m": radius_km * 1000}
    if exclude_id is not None:
        query += " AND id != :exclude_id"
        params["exclude_id"] = str(exclude_id)
    return db.execute(text(query), params).scalar_one()
