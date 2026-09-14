from tests.conftest import login


def test_field_officer_cannot_run_satellite_scan(client):
    token = login(client, "officer@naimos.gov.gh")
    resp = client.post(
        "/api/satellite/scan",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 9.4, "longitude": -0.8},
    )
    assert resp.status_code == 403


def test_satellite_scan_persists_detection_and_computes_risk(client):
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.post(
        "/api/satellite/scan",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 9.55, "longitude": -0.95},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert 0 <= body["risk_score"] <= 100
    assert body["detection_type"] in {
        "EXCAVATION", "EXPOSED_SOIL", "VEGETATION_LOSS", "PIT_EXPANSION", "NEW_ROAD", "WATER_SEDIMENTATION",
    }
    assert 0 <= body["confidence"] <= 1
    assert body["requires_verification"] is True
    assert "SIMULATED" in body["disclaimer"]
    assert body["previous_observation"]["is_simulated"] is True
    assert body["current_observation"]["is_simulated"] is True

    history = client.get(
        f"/api/satellite/history?lat=9.55&lon=-0.95&radius_km=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history.status_code == 200
    assert any(d["id"] == body["ai_detection_id"] for d in history.json())


def test_repeated_same_day_scan_is_deterministic(client):
    token = login(client, "analyst@naimos.gov.gh")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"latitude": 8.2, "longitude": -1.6}

    first = client.post("/api/satellite/scan", headers=headers, json=payload).json()
    second = client.post("/api/satellite/scan", headers=headers, json=payload).json()

    assert first["detection_type"] == second["detection_type"]
    assert first["confidence"] == second["confidence"]
    assert first["estimated_area_hectares"] == second["estimated_area_hectares"]
    # A second detection at the same spot should never lower the risk score.
    assert second["risk_score"] >= first["risk_score"]
