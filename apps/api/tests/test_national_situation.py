from tests.conftest import login


def test_pro_can_view_national_situation(client):
    token = login(client, "pro@naimos.gov.gh")
    resp = client.get("/api/analytics/national-situation", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    for key in (
        "active_investigations", "high_risk_locations", "field_operations",
        "incidents_this_month", "water_bodies_affected", "forest_areas_affected",
    ):
        assert isinstance(body[key], int)

    assert isinstance(body["top_hotspots"], list)
    assert len(body["top_hotspots"]) > 0
    for h in body["top_hotspots"]:
        assert h["risk_score"] is not None
        assert h["priority_label"] in {"Critical", "High", "Elevated", "Moderate", "Low"}


def test_hotspots_sorted_by_risk_score_descending(client):
    token = login(client, "pro@naimos.gov.gh")
    resp = client.get("/api/analytics/national-situation", headers={"Authorization": f"Bearer {token}"})
    scores = [h["risk_score"] for h in resp.json()["top_hotspots"]]
    assert scores == sorted(scores, reverse=True)


def test_field_officer_cannot_view_national_situation(client):
    """This is the PRO-specific dashboard - not every role should see it."""
    token = login(client, "officer@naimos.gov.gh")
    resp = client.get("/api/analytics/national-situation", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_super_admin_can_view_national_situation(client):
    token = login(client, "admin@naimos.gov.gh")
    resp = client.get("/api/analytics/national-situation", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
