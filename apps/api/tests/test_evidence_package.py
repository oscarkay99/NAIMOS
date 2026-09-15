from tests.conftest import login


def _incident_with_evidence(client, token) -> str:
    """The seeded Ankobra hotspot always has at least one demo evidence item."""
    resp = client.get("/api/incidents?search=Ankobra", headers={"Authorization": f"Bearer {token}"})
    return resp.json()[0]["id"]


def test_analyst_can_generate_evidence_package(client):
    token = login(client, "analyst@naimos.gov.gh")
    incident_id = _incident_with_evidence(client, token)

    resp = client.post(f"/api/incidents/{incident_id}/evidence-package", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["report_type"] == "evidence_package"
    assert "INCIDENT SUMMARY" in body["content_markdown"]
    assert "AI-DETECTED EVIDENCE" in body["content_markdown"]
    assert "EVIDENCE FILES" in body["content_markdown"]
    assert "PHOTO-001" in body["content_markdown"]


def test_field_officer_cannot_generate_evidence_package(client):
    token = login(client, "officer@naimos.gov.gh")
    incident_id = _incident_with_evidence(client, token)

    resp = client.post(f"/api/incidents/{incident_id}/evidence-package", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_evidence_package_never_sums_counts_across_files(client, db):
    """Regression guard for the aggregation rule: the reported quantity for
    a countable class must be the max seen in any one file, never a sum -
    summing would risk claiming duplicate objects across overlapping photos."""
    from app.services.evidence.aggregator import ConsolidatedDetection, build_evidence_package
    from app.models.incident import Incident
    from sqlalchemy import select

    token = login(client, "analyst@naimos.gov.gh")
    incident_id = _incident_with_evidence(client, token)
    incident = db.execute(select(Incident).where(Incident.id == incident_id)).scalar_one()

    package = build_evidence_package(db, incident)
    db.rollback()  # this test only inspects aggregation logic, not persistence

    for detection in package.consolidated:
        if detection.max_count is not None:
            assert detection.max_count <= 3  # matches the mock provider's max per-file quantity
