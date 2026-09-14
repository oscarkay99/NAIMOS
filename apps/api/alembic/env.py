from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.models import Base  # noqa: F401 (registers all models)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


_MANUAL_SPATIAL_INDEXES = {
    "idx_regions_centroid", "idx_districts_centroid", "idx_communities_location",
    "idx_water_bodies_geom", "idx_protected_areas_geom", "idx_forest_reserves_geom",
    "idx_incidents_location", "idx_ai_detections_location", "idx_risk_scores_location",
    "idx_evidence_location", "idx_field_reports_location",
}


def include_object(object, name, type_, reflected, compare_to):
    # PostGIS system table - not part of the application schema.
    if type_ == "table" and name == "spatial_ref_sys":
        return False
    # GIST indexes on Geometry columns (spatial_index=False) are created by
    # hand in the initial migration and aren't declared in the ORM metadata -
    # skip them so autogenerate doesn't propose dropping them every time.
    if type_ == "index" and name in _MANUAL_SPATIAL_INDEXES:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
