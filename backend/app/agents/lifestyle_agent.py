from app.agents.base_agent import BaseAgent


class LifestyleAgent(BaseAgent):
    agent_type = "lifestyle"

    def _build_prompt(self, ocr_text: str, user_profile: dict) -> str:
        language = user_profile.get("language", "hi")
        return f"""
Medical document text:
{ocr_text}

In {language}, give 3 simple lifestyle tips (food, rest, activity) that can help with this condition.
Tips must be practical for a rural Indian household. No medical jargon.
Return a JSON object with key: "tips" (list of 3 strings).
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
        return {"tips": [raw.strip()]}
