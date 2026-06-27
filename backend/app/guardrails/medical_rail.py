import re

BLOCKED_PATTERNS = [
    r"\b\d+\s*mg\b",
    r"\b\d+\s*ml\b",
    r"\btake\s+\d+\b",
    r"\bdose\b",
    r"\bdosage\b",
    r"\bprescri(be|ption|bed)\b",
    r"\byou have\s+(diabetes|cancer|tuberculosis|typhoid|dengue|malaria)\b",
    r"\bdiagnos(is|ed|e)\b",
    r"\bconfirm(ed)?\s+(diagnosis|disease|condition)\b",
]

MEDICINE_KEYWORDS = [
    "paracetamol", "ibuprofen", "amoxicillin", "metformin", "atorvastatin",
    "aspirin", "omeprazole", "azithromycin", "ciprofloxacin", "dolo",
    "crocin", "disprin", "combiflam", "cetrizine", "pantoprazole",
    "ramipril", "amlodipine", "metoprolol", "atenolol", "glipizide",
    "insulin", "warfarin", "lisinopril", "losartan", "hydrochlorothiazide",
]

_medicine_pattern = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in MEDICINE_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

_blocked_pattern = re.compile(
    "|".join(BLOCKED_PATTERNS),
    re.IGNORECASE,
)


def check(text: str) -> tuple[bool, str | None]:
    medicine_match = _medicine_pattern.search(text)
    if medicine_match:
        return False, f"Response mentions medicine: {medicine_match.group()}"

    blocked_match = _blocked_pattern.search(text)
    if blocked_match:
        return False, "Response contains blocked medical content"

    return True, None
