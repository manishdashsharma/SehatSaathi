import pytest
from app.guardrails import medical_rail, language_rail, emergency_detector


def test_medical_rail_blocks_medicine_name():
    ok, reason = medical_rail.check("You should take paracetamol 500mg twice a day.")
    assert ok is False
    assert reason is not None


def test_medical_rail_blocks_dosage_pattern():
    ok, reason = medical_rail.check("Take 2 tablets every 8 hours.")
    assert ok is False


def test_medical_rail_allows_clean_response():
    ok, _ = medical_rail.check(
        "Your document shows some signs of high blood sugar. Please see a doctor soon."
    )
    assert ok is True


def test_language_rail_blocks_jargon():
    ok, reason = language_rail.check("The pathophysiology of this condition is complex.")
    assert ok is False


def test_language_rail_allows_simple_text():
    ok, _ = language_rail.check(
        "Your blood test shows your sugar is a bit high. Eat less sweet things and rest well."
    )
    assert ok is True


def test_emergency_detector_flags_chest_pain():
    flagged, score = emergency_detector.is_emergency("I have severe chest pain right now.")
    assert flagged is True
    assert score > 1.5


def test_emergency_detector_flags_hindi_keywords():
    flagged, score = emergency_detector.is_emergency("मुझे सीने में दर्द है।")
    assert flagged is True


def test_emergency_detector_no_flag_normal():
    flagged, score = emergency_detector.is_emergency("My knee hurts a little after walking.")
    assert flagged is False


def test_emergency_score_returns_float():
    _, score = emergency_detector.is_emergency("I have a mild headache.")
    assert isinstance(score, float)
