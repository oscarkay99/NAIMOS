import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app


@pytest.fixture(autouse=True)
def force_mock_satellite_provider(monkeypatch):
    """Tests must be hermetic and never depend on live external API calls -
    force MockSatelliteProvider regardless of whether real Sentinel Hub
    credentials happen to be configured in this environment's .env."""
    from app.services.satellite.mock_provider import MockSatelliteProvider

    monkeypatch.setattr(
        "app.services.satellite.provider.get_satellite_provider", lambda: MockSatelliteProvider()
    )
    monkeypatch.setattr(
        "app.api.routes.satellite.get_satellite_provider", lambda: MockSatelliteProvider()
    )


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def login(client: TestClient, email: str, password: str = "Demo@1234") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
