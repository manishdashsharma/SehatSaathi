from abc import ABC, abstractmethod
from groq import AsyncGroq
from openai import AsyncOpenAI
from app.config import get_settings
from app.services import guardrail_service
from app.utils.language_utils import get_agent_system_prompt
import structlog

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    agent_type: str = "base"

    def __init__(self) -> None:
        settings = get_settings()
        self._groq = AsyncGroq(api_key=settings.groq_api_key)

    @abstractmethod
    def _build_prompt(self, ocr_text: str, user_profile: dict) -> str:
        ...

    @abstractmethod
    def _parse_response(self, raw: str) -> dict:
        ...

    async def run(self, ocr_text: str, user_profile: dict) -> dict:
        prompt = self._build_prompt(ocr_text, user_profile)
        raw_response = await self._call_llm(prompt)
        guardrail_service.validate_response(raw_response)
        verdict = self._parse_response(raw_response)
        return {
            "agent_type": self.agent_type,
            "verdict": verdict,
            "raw_response": raw_response,
            "passed_guardrail": True,
        }

    async def _call_llm(self, prompt: str) -> str:
        try:
            response = await self._groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": get_agent_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("groq_call_failed", agent=self.agent_type, error=str(exc))
            raise
