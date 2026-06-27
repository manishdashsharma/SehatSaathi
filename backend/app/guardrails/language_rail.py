import re

JARGON_WORDS = [
    "pathophysiology", "etiology", "prognosis", "contraindicated",
    "pharmacokinetics", "bioavailability", "hemodynamic", "idiopathic",
    "iatrogenic", "comorbidity", "dyslipidemia", "thrombocytopenia",
    "hypertrophic", "cardiomyopathy", "nephropathy", "neuropathy",
    "hepatotoxicity", "nephrotoxicity", "anaphylaxis", "thrombosis",
    "embolism", "ischemia", "infarction", "septicemia", "bacteremia",
]

_jargon_pattern = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in JARGON_WORDS) + r")\b",
    re.IGNORECASE,
)

MAX_AVG_WORD_LENGTH = 8
MIN_SIMPLE_SCORE = 0.6


def score(text: str) -> float:
    words = re.findall(r"\b[a-zA-Z]+\b", text)
    if not words:
        return 1.0
    jargon_count = sum(1 for w in words if _jargon_pattern.match(w))
    avg_len = sum(len(w) for w in words) / len(words)
    jargon_penalty = jargon_count / len(words)
    length_penalty = max(0, (avg_len - MAX_AVG_WORD_LENGTH) / MAX_AVG_WORD_LENGTH)
    return max(0.0, 1.0 - jargon_penalty - length_penalty * 0.3)


def check(text: str) -> tuple[bool, str | None]:
    jargon_match = _jargon_pattern.search(text)
    if jargon_match:
        return False, f"Response contains medical jargon: {jargon_match.group()}"

    simplicity = score(text)
    if simplicity < MIN_SIMPLE_SCORE:
        return False, f"Response language too complex (score: {simplicity:.2f})"

    return True, None
