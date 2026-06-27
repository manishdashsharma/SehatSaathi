from app.agents.base_agent import BaseAgent


class DiagnosisAgent(BaseAgent):
    agent_type = "diagnosis"

    def _build_prompt(self, ocr_text: str, user_profile: dict) -> str:
        language = user_profile.get("language", "hi")
        return f"""
Medical document text:
{ocr_text}

In {language}, explain in 3-4 simple sentences what health concern this document is about.
Do NOT name any medicine. Do NOT confirm any diagnosis. Do NOT give any dosage.
Return a JSON object with keys: "summary" (string), "key_findings" (list of strings, max 3).
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
        return {"summary": raw.strip(), "key_findings": []}
