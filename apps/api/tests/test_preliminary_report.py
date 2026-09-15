from tests.conftest import login


def _get_first_incident_id(client, token) -> str:
    resp = client.get("/api/incidents?limit=1", headers={"Authorization": f"Bearer {token}"})
    return resp.json()[0]["id"]


def test_field_officer_can_generate_preliminary_report(client):
    token = login(client, "officer@naimos.gov.gh")
    incident_id = _get_first_incident_id(client, token)

    resp = client.post(f"/api/incidents/{incident_id}/preliminary-report", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["report_type"] == "preliminary_field_report"
    assert "OFFICER-REPORTED FACTS" in body["content_markdown"]
    assert "RECOMMENDED CLASSIFICATION" in body["content_markdown"]
    assert incident_id in body["source_incident_ids"]


def test_pro_cannot_generate_preliminary_report(client):
    token = login(client, "pro@naimos.gov.gh")
    incident_id = _get_first_incident_id(client, token)

    resp = client.post(f"/api/incidents/{incident_id}/preliminary-report", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_get_preliminary_report_returns_none_before_generation(client):
    token = login(client, "officer@naimos.gov.gh")
    # Use the incident least likely to already have a report from another test's side effects.
    resp = client.get("/api/incidents?limit=50", headers={"Authorization": f"Bearer {token}"})
    incidents = resp.json()
    target_id = incidents[-1]["id"]

    get_resp = client.get(f"/api/incidents/{target_id}/preliminary-report", headers={"Authorization": f"Bearer {token}"})
    assert get_resp.status_code == 200
    first = get_resp.json()

    gen_resp = client.post(f"/api/incidents/{target_id}/preliminary-report", headers={"Authorization": f"Bearer {token}"})
    assert gen_resp.status_code == 200

    get_resp2 = client.get(f"/api/incidents/{target_id}/preliminary-report", headers={"Authorization": f"Bearer {token}"})
    assert get_resp2.json() is not None
    assert get_resp2.json()["id"] == gen_resp.json()["id"]
