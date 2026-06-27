import re

EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "can't breathe", "cannot breathe",
    "unconscious", "not breathing", "stopped breathing", "seizure",
    "stroke", "paralysis", "heavy bleeding", "uncontrolled bleeding",
    "poisoning", "overdose", "suicidal", "suicide", "want to die",
    "severe pain", "extremely severe", "emergency",
    "सीने में दर्द", "दिल का दौरा", "सांस नहीं", "बेहोश",
    "दौरा", "लकवा", "बहुत खून", "जहर", "मरना चाहता",
    "छाती में दर्द", "बहुत तेज दर्द",
]

_keyword_pattern = re.compile(
    r"(" + "|".join(re.escape(k) for k in EMERGENCY_KEYWORDS) + r")",
    re.IGNORECASE,
)

SEVERITY_MULTIPLIERS = {
    "chest pain": 2.0,
    "heart attack": 3.0,
    "not breathing": 3.0,
    "stopped breathing": 3.0,
    "unconscious": 2.5,
    "suicidal": 3.0,
    "suicide": 3.0,
    "want to die": 3.0,
    "seizure": 2.5,
    "overdose": 2.5,
    "सीने में दर्द": 2.0,
    "दिल का दौरा": 3.0,
    "सांस नहीं": 3.0,
    "बेहोश": 2.5,
    "दौरा": 2.5,
    "लकवा": 2.5,
    "मरना चाहता": 3.0,
    "छाती में दर्द": 2.0,
    "बहुत तेज दर्द": 2.0,
}

EMERGENCY_THRESHOLD = 1.5


def score(text: str) -> float:
    matches = _keyword_pattern.findall(text.lower())
    if not matches:
        return 0.0
    total = sum(SEVERITY_MULTIPLIERS.get(m, 1.0) for m in matches)
    return min(total, 10.0)


def is_emergency(text: str) -> tuple[bool, float]:
    emergency_score = score(text)
    return emergency_score >= EMERGENCY_THRESHOLD, emergency_score
