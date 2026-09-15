from tests.conftest import login


def test_leaderboard_is_sorted_by_probability_descending(client):
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.get("/api/predictions/leaderboard?limit=50", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) > 0
    probabilities = [r["probability"] for r in rows]
    assert probabilities == sorted(probabilities, reverse=True)


def test_probability_never_claims_certainty(client):
    """Guardrail: an AI-generated projection about the future must never
    claim 100% certainty."""
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.get("/api/predictions/leaderboard?limit=50", headers={"Authorization": f"Bearer {token}"})
    rows = resp.json()
    assert all(r["probability"] <= 95 for r in rows)


def test_leaderboard_entries_have_expected_fields(client):
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.get("/api/predictions/leaderboard?limit=50", headers={"Authorization": f"Bearer {token}"})
    rows = resp.json()
    assert rows
    for row in rows:
        assert row["category"] in {"CRITICAL", "HIGH", "ELEVATED", "MODERATE", "LOW"}
        assert row["expected_development"]
        assert row["recommendation"]


def test_seeded_flagship_hotspot_has_expansion_signals(client):
    """The Tarkwa-Nsuaem / Ankobra River hotspot (NAIMOS-2026-000101) is
    seeded with a rising risk trend, a NEW_ROAD detection, land-disturbance
    detections, nearby prior incidents, water proximity, and equipment
    reports - it should surface with a non-trivial probability and multiple
    named factors, not a flat zero."""
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.get("/api/predictions/leaderboard?limit=50", headers={"Authorization": f"Bearer {token}"})
    rows = resp.json()
    target = next(r for r in rows if r["reference_number"] == "NAIMOS-2026-000101")
    assert target["probability"] > 0
    assert len(target["factors"]) >= 2
    labels = {f["label"] for f in target["factors"]}
    assert "New access route detected" in labels


def test_field_supervisor_cannot_recalculate_but_can_view_leaderboard(client):
    token = login(client, "supervisor@naimos.gov.gh")
    recalc = client.post("/api/predictions/recalculate", headers={"Authorization": f"Bearer {token}"})
    assert recalc.status_code == 403

    leaderboard = client.get("/api/predictions/leaderboard", headers={"Authorization": f"Bearer {token}"})
    assert leaderboard.status_code == 200


def test_recalculate_appends_new_snapshot_without_losing_history(client, db):
    from sqlalchemy import select

    from app.models.ai import ExpansionPrediction

    token = login(client, "analyst@naimos.gov.gh")
    before_count = len(db.execute(select(ExpansionPrediction)).scalars().all())

    resp = client.post("/api/predictions/recalculate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["recalculated_count"] > 0

    db.expire_all()
    after_count = len(db.execute(select(ExpansionPrediction)).scalars().all())
    assert after_count > before_count


def test_get_incident_prediction_detail(client):
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.get("/api/incidents?limit=1", headers={"Authorization": f"Bearer {token}"})
    incident_id = resp.json()[0]["id"]

    detail = client.get(f"/api/predictions/incidents/{incident_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.status_code == 200
    body = detail.json()
    assert "explanation" in body
    assert "requires field verification" in body["explanation"] or "not a certainty" in body["explanation"]


def test_report_viewer_cannot_recalculate(client):
    token = login(client, "viewer@naimos.gov.gh")
    resp = client.post("/api/predictions/recalculate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
