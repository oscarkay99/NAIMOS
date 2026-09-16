from tests.conftest import login


def test_audit_logs_returns_paginated_envelope(client):
    token = login(client, "auditor@naimos.gov.gh")
    resp = client.get("/api/audit-logs?limit=5", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()

    assert set(body.keys()) == {"items", "total", "limit", "offset"}
    assert body["limit"] == 5
    assert body["offset"] == 0
    assert len(body["items"]) <= 5
    assert body["total"] >= len(body["items"])


def test_audit_logs_pages_do_not_overlap(client):
    token = login(client, "auditor@naimos.gov.gh")
    headers = {"Authorization": f"Bearer {token}"}

    page1 = client.get("/api/audit-logs?limit=3&offset=0", headers=headers).json()
    page2 = client.get("/api/audit-logs?limit=3&offset=3", headers=headers).json()

    assert page1["total"] == page2["total"]
    ids1 = {row["id"] for row in page1["items"]}
    ids2 = {row["id"] for row in page2["items"]}
    if ids1 and ids2:
        assert ids1.isdisjoint(ids2)


def test_audit_logs_ordered_most_recent_first(client):
    token = login(client, "auditor@naimos.gov.gh")
    resp = client.get("/api/audit-logs?limit=20", headers={"Authorization": f"Bearer {token}"})
    timestamps = [row["created_at"] for row in resp.json()["items"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_incidents_list_stays_a_plain_array(client):
    """Backward compatibility: other pages (e.g. the dashboard) fetch this
    endpoint expecting a bare array, not an envelope - that shape must not
    change even though pagination metadata is now available."""
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.get("/api/incidents?limit=5", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_incidents_total_count_header_matches_real_total(client):
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.get("/api/incidents?limit=200", headers={"Authorization": f"Bearer {token}"})
    total_header = int(resp.headers["x-total-count"])
    # limit=200 comfortably exceeds seeded row count, so the page holds every row
    assert total_header == len(resp.json())


def test_incidents_total_count_header_reflects_filters_not_page_size(client):
    token = login(client, "analyst@naimos.gov.gh")
    headers = {"Authorization": f"Bearer {token}"}

    unfiltered = client.get("/api/incidents?limit=1", headers=headers)
    filtered = client.get("/api/incidents?limit=1&status=CLOSED", headers=headers)

    total_all = int(unfiltered.headers["x-total-count"])
    total_closed = int(filtered.headers["x-total-count"])
    assert len(unfiltered.json()) == 1  # page size, not the total
    assert total_closed <= total_all


def test_incidents_pages_do_not_overlap(client):
    token = login(client, "analyst@naimos.gov.gh")
    headers = {"Authorization": f"Bearer {token}"}

    page1 = client.get("/api/incidents?limit=3&offset=0", headers=headers).json()
    page2 = client.get("/api/incidents?limit=3&offset=3", headers=headers).json()

    ids1 = {row["id"] for row in page1}
    ids2 = {row["id"] for row in page2}
    if ids1 and ids2:
        assert ids1.isdisjoint(ids2)
