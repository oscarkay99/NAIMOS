from app.services.ai.nl_query import detect_intent


def test_named_water_body_with_radius_and_time_window():
    q = "Show me illegal mining incidents within 5 km of the Pra River during the last 30 days."
    assert detect_intent(q) == "incidents_near_named_water_time"


def test_fastest_increasing_risk():
    q = "Which areas have experienced the fastest increase in suspected mining activity?"
    assert detect_intent(q) == "fastest_increasing_risk"


def test_top_n_field_verification():
    q = "Give me the top 10 locations requiring field verification this week."
    assert detect_intent(q) == "top_n_field_verification"


def test_equipment_and_region():
    q = "Summarise all incidents involving excavators in the Western Region."
    assert detect_intent(q) == "incidents_by_equipment_region"


def test_equipment_intent_does_not_shadow_generic_region_summary():
    """A region question with no equipment mention should still hit the
    original, more general region_summary intent."""
    assert detect_intent("Summarise Western Region activity") == "region_summary"


def test_named_water_intent_does_not_shadow_generic_near_water():
    """A generic 'near water' question with no radius/named river should
    still hit the original incidents_near_water intent."""
    assert detect_intent("What incidents are near water bodies?") == "incidents_near_water"


def test_existing_intents_still_match_after_new_ones_added():
    assert detect_intent("Show emerging hotspots") == "emerging_hotspots"
    assert detect_intent("Which districts had the most verified incidents this month?") == "districts_most_verified"
    assert detect_intent("Generate a briefing for today's operations meeting") == "todays_briefing"


def test_unrecognized_question_returns_none():
    assert detect_intent("What is the weather like today?") is None
