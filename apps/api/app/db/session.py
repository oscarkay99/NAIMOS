from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Separate engine bound to the naimos_readonly Postgres role. Used only by the
# AI natural-language query pipeline (app/services/ai/nl_query.py) so that no
# AI-generated query can ever mutate data, regardless of application bugs.
readonly_engine = create_engine(settings.database_url_readonly, pool_pre_ping=True, future=True)
ReadOnlySessionLocal = sessionmaker(bind=readonly_engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_readonly_db() -> Generator[Session, None, None]:
    db = ReadOnlySessionLocal()
    try:
        yield db
    finally:
        db.close()
