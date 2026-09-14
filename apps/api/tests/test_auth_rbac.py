from tests.conftest import login


def test_login_rejects_bad_password(client):
    resp = client.post("/api/auth/login", json={"email": "admin@naimos.gov.gh", "password": "wrong"})
    assert resp.status_code == 401


def test_login_succeeds_and_returns_tokens(client):
    resp = client.post("/api/auth/login", json={"email": "admin@naimos.gov.gh", "password": "Demo@1234"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body and "refresh_token" in body


def test_unauthenticated_request_is_rejected(client):
    resp = client.get("/api/incidents")
    assert resp.status_code == 401


def test_field_officer_cannot_view_audit_logs(client):
    """RBAC section 23/39: server-side permission check must deny, regardless
    of any frontend-only gating."""
    token = login(client, "officer@naimos.gov.gh")
    resp = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_auditor_can_view_audit_logs_but_not_create_incidents(client):
    token = login(client, "auditor@naimos.gov.gh")
    resp = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    resp2 = client.post(
        "/api/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Should be denied", "latitude": 5.0, "longitude": -1.0},
    )
    assert resp2.status_code == 403


def test_pro_can_generate_report_but_cannot_change_incident_status(client):
    token = login(client, "pro@naimos.gov.gh")
    resp = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={"report_type": "executive_brief"},
    )
    assert resp.status_code == 200

    incidents = client.get("/api/incidents?limit=1", headers={"Authorization": f"Bearer {token}"}).json()
    incident_id = incidents[0]["id"]
    resp2 = client.post(
        f"/api/incidents/{incident_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_status": "VERIFIED", "reason": "should be denied"},
    )
    assert resp2.status_code == 403
