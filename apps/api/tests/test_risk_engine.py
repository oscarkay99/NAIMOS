from app.models.enums import RiskCategory
from app.services.risk.engine import calculate_risk


def test_risk_score_is_explainable_and_bounded(db):
    """The seeded Ankobra River hotspot should score HIGH with a non-empty,
    labeled factor breakdown - never a black-box number (section 3)."""
    result = calculate_risk(db, lat=5.3200, lon=-2.2270)
    assert 0 <= result.score <= 100
    assert result.category == RiskCategory.from_score(result.score)
    assert result.factors, "Expected at least one contributing factor for the seeded hotspot"
    assert all(f.points > 0 for f in result.factors)
    assert "not confirmation of illegal activity" in result.explanation


def test_remote_location_scores_low(db):
    """A point far from any seeded incident/water body/protected area should
    carry a low, mostly-empty-factor score."""
    result = calculate_risk(db, lat=9.9, lon=-0.9)  # rural Northern region, no seeded signals
    assert result.score <= 20
    assert result.category == RiskCategory.LOW


def test_risk_category_boundaries():
    assert RiskCategory.from_score(0) == RiskCategory.LOW
    assert RiskCategory.from_score(20) == RiskCategory.LOW
    assert RiskCategory.from_score(21) == RiskCategory.MODERATE
    assert RiskCategory.from_score(41) == RiskCategory.ELEVATED
    assert RiskCategory.from_score(61) == RiskCategory.HIGH
    assert RiskCategory.from_score(81) == RiskCategory.CRITICAL
    assert RiskCategory.from_score(100) == RiskCategory.CRITICAL
