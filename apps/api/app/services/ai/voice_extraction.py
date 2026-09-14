"""Rule-based structured extraction from a voice-note transcript (section 10).
Deliberately simple pattern matching rather than a black-box LLM call, so
results are explainable and reproducible for the demo. The officer must
review and approve the result before it becomes part of the record - this
function only proposes a draft."""

import re

from app.schemas.field_report import VoiceExtraction

_TIME_RE = re.compile(r"\b(\d{1,2}[:.]\d{2})\b|\b(\d{1,2})\s*(am|pm|o'?clock)\b", re.I)
_EQUIPMENT_TERMS = ["excavator", "bulldozer", "changfan", "chanfan", "dredge", "pump", "truck", "generator"]
_WATER_TERMS = ["river", "stream", "lake", "lagoon", "creek", "water body"]
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
}


def _extract_count_before(term: str, text: str) -> str:
    pattern = re.compile(r"(\d+|" + "|".join(_NUMBER_WORDS) + r")\s+" + term + "s?", re.I)
    match = pattern.search(text)
    if not match:
        return term.capitalize()
    qty = match.group(1).lower()
    qty = str(_NUMBER_WORDS.get(qty, qty))
    return f"{qty} {term}{'s' if qty != '1' else ''}"


def extract_structured(transcript: str) -> VoiceExtraction:
    time_match = _TIME_RE.search(transcript)
    time_mentioned = time_match.group(0) if time_match else None

    equipment = [
        _extract_count_before(term, transcript)
        for term in _EQUIPMENT_TERMS
        if re.search(rf"\b{term}", transcript, re.I)
    ]

    water_match = None
    for term in _WATER_TERMS:
        if term in transcript.lower():
            water_match = term
            break

    activity_summary = "Suspected mining-related activity" if equipment else "No equipment mentioned"

    return VoiceExtraction(
        time_mentioned=time_mentioned,
        equipment_mentioned=equipment,
        water_body_mentioned=f"Nearby {water_match}" if water_match else None,
        activity_summary=activity_summary,
        status="Requires verification",
    )
