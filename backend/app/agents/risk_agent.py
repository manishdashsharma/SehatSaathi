from app.agents.base_agent import BaseAgent


class RiskAgent(BaseAgent):
    agent_type = "risk"

    def _build_prompt(self, ocr_text: str, user_profile: dict) -> str:
        language = user_profile.get("language", "hi")
        return f"""
Medical document text:
{ocr_text}

In {language}, assess the urgency of this health situation in simple words.
Return a JSON object with keys:
  "urgency_level": one of "low", "medium", "high",
  "should_see_doctor": boolean,
  "urgency_reason": string (1-2 simple sentences explaining why).
Do NOT name medicines. Do NOT confirm diagnosis.
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
        return {
            "urgency_level": "medium",
            "should_see_doctor": True,
            "urgency_reason": raw.strip(),
        }
