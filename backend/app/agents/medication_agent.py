from app.agents.base_agent import BaseAgent


class MedicationAgent(BaseAgent):
    agent_type = "medication"

    def _build_prompt(self, ocr_text: str, user_profile: dict) -> str:
        language = user_profile.get("language", "hi")
        return f"""
Medical document text:
{ocr_text}

In {language}, explain in simple words what types of treatments or care this document mentions.
Do NOT name any specific medicine. Do NOT give dosage. Do NOT say "take X".
Return a JSON object with keys: "treatment_types" (list of strings), "care_advice" (string).
"""

    def _parse_response(self, raw: str) -> dict:
        import json
        import re

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"treatment_types": [], "care_advice": raw.strip()}
