from tests.conftest import login


def test_leaderboard_is_sorted_by_score_descending(client):
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.get("/api/risk/leaderboard?limit=50", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) > 0
    scores = [r["score"] for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_leaderboard_entries_have_priority_and_change_fields(client):
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.get("/api/risk/leaderboard?limit=50", headers={"Authorization": f"Bearer {token}"})
    rows = resp.json()
    assert rows
    for row in rows:
        assert row["priority_label"] in {"Critical", "High", "Elevated", "Moderate", "Low"}
        assert row["priority_emoji"]
        assert row["change_pct"] is None or isinstance(row["change_pct"], (int, float))

    # Seeded incidents carry an 8-day-old historical snapshot, so at least
    # some rows should have a real (non-null) change_pct - only incidents
    # created after seeding (with no week-old history yet) legitimately
    # show None.
    assert any(row["change_pct"] is not None for row in rows)


def test_leaderboard_excludes_closed_incidents_by_default(client):
    token = login(client, "analyst@naimos.gov.gh")
    resp = client.get("/api/risk/leaderboard?limit=50", headers={"Authorization": f"Bearer {token}"})
    rows = resp.json()
    assert all(r["status"] not in ("CLOSED", "ARCHIVED") for r in rows)


def test_field_officer_cannot_recalculate_but_can_view_leaderboard(client):
    token = login(client, "officer@naimos.gov.gh")
    recalc = client.post("/api/risk/recalculate", headers={"Authorization": f"Bearer {token}"})
    assert recalc.status_code == 403

    leaderboard = client.get("/api/risk/leaderboard", headers={"Authorization": f"Bearer {token}"})
    assert leaderboard.status_code == 200


def test_recalculate_appends_new_snapshot_without_losing_history(client, db):
    from sqlalchemy import select

    from app.models.ai import RiskScore

    token = login(client, "analyst@naimos.gov.gh")
    before = db.execute(select(RiskScore)).scalars().all()
    before_count = len(before)

    resp = client.post("/api/risk/recalculate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["recalculated_count"] > 0

    db.expire_all()
    after_count = len(db.execute(select(RiskScore)).scalars().all())
    assert after_count > before_count  # appended, not overwritten
