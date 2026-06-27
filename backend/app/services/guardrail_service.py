from app.guardrails import medical_rail, language_rail, emergency_detector
from app.core.exceptions import GuardrailError


def validate_response(text: str, check_language: bool = True) -> None:
    medical_ok, medical_reason = medical_rail.check(text)
    if not medical_ok:
        raise GuardrailError(medical_reason or "Medical guardrail violation")

    if check_language:
        lang_ok, lang_reason = language_rail.check(text)
        if not lang_ok:
            raise GuardrailError(lang_reason or "Language guardrail violation")


def check_emergency(text: str) -> tuple[bool, float]:
    return emergency_detector.is_emergency(text)


def validate_input(text: str) -> None:
    flagged, _ = emergency_detector.is_emergency(text)
    if flagged:
        return
    if len(text.strip()) < 5:
        raise GuardrailError("Input too short")
