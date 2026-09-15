from tests.conftest import login


def _generate(client, token, report_type):
    resp = client.post(
        "/api/reports/generate",
        json={"report_type": report_type},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_press_briefing_is_prose_not_bullet_dump(client):
    token = login(client, "pro@naimos.gov.gh")
    body = _generate(client, token, "press_briefing")
    assert "NAIMOS" in body["content_markdown"]
    assert "VERIFIED FACTS" not in body["content_markdown"]


def test_social_media_briefing_is_short(client):
    token = login(client, "pro@naimos.gov.gh")
    body = _generate(client, token, "social_media_briefing")
    assert len(body["content_markdown"]) < 600


def test_parliamentary_briefing_uses_formal_address(client):
    token = login(client, "pro@naimos.gov.gh")
    body = _generate(client, token, "parliamentary_briefing")
    assert "Honourable Members" in body["content_markdown"]
    assert "VERIFIED FIGURES" in body["content_markdown"]


def test_media_qa_produces_question_answer_pairs(client):
    token = login(client, "pro@naimos.gov.gh")
    body = _generate(client, token, "media_qa")
    assert body["content_markdown"].count("**Q:") >= 5
    assert "does not fabricate seizure figures" in body["content_markdown"]


def test_talking_points_is_bullet_list(client):
    token = login(client, "pro@naimos.gov.gh")
    body = _generate(client, token, "talking_points")
    assert body["content_markdown"].count("\n- ") >= 3


def test_different_report_types_produce_different_content(client):
    token = login(client, "pro@naimos.gov.gh")
    press = _generate(client, token, "press_briefing")
    social = _generate(client, token, "social_media_briefing")
    assert press["content_markdown"] != social["content_markdown"]


def test_report_viewer_cannot_generate_communications(client):
    token = login(client, "viewer@naimos.gov.gh")
    resp = client.post(
        "/api/reports/generate",
        json={"report_type": "press_briefing"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
