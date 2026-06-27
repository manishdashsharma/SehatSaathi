import asyncio
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import groq as groq_plugin, openai as openai_plugin
from app.config import get_settings
from app.utils.language_utils import get_system_prompt
import structlog

logger = structlog.get_logger(__name__)


class SehatSaathiVoiceAgent(Agent):
    def __init__(self, system_prompt: str) -> None:
        super().__init__(instructions=system_prompt)


async def run_voice_agent(room_name: str, verdicts: list[dict], language: str) -> None:
    settings = get_settings()
    system_prompt = _build_voice_prompt(verdicts, language)

    async def entrypoint(ctx):
        agent = SehatSaathiVoiceAgent(system_prompt=system_prompt)
        session = AgentSession(
            stt=groq_plugin.STT(model="whisper-large-v3"),
            llm=groq_plugin.LLM(model="llama-3.3-70b-versatile"),
            tts=openai_plugin.TTS(voice="nova"),
        )
        await session.start(ctx.room, agent=agent, room_input_options=RoomInputOptions())
        await session.generate_reply(
            instructions=_welcome_message(language)
        )

    from livekit.agents import WorkerOptions, cli
    worker_options = WorkerOptions(
        entrypoint_fnc=entrypoint,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
        ws_url=settings.livekit_url,
    )
    logger.info("voice_agent_starting", room=room_name, language=language)
    asyncio.create_task(_run_worker(worker_options))


async def _run_worker(worker_options) -> None:
    from livekit.agents import Worker
    worker = Worker(worker_options)
    await worker.run()


def _build_voice_prompt(verdicts: list[dict], language: str) -> str:
    base = get_system_prompt(language)
    summary_parts = []
    for v in verdicts:
        agent_type = v.get("agent_type", "")
        verdict_data = v.get("verdict", {})
        if agent_type == "diagnosis":
            summary_parts.append(f"Document summary: {verdict_data.get('summary', '')}")
            findings = verdict_data.get("key_findings", [])
            if findings:
                summary_parts.append(f"Key findings: {'; '.join(findings)}")
        elif agent_type == "medication":
            care = verdict_data.get("care_advice", "")
            if care:
                summary_parts.append(f"Care advice: {care}")
        elif agent_type == "lifestyle":
            tips = verdict_data.get("tips", [])
            if tips:
                summary_parts.append(f"Lifestyle tips: {'; '.join(tips)}")
        elif agent_type == "risk":
            summary_parts.append(
                f"Urgency: {verdict_data.get('urgency_level', 'medium')} — "
                f"{verdict_data.get('urgency_reason', '')}"
            )

    context = "\n".join(summary_parts)
    return f"{base}\n\nDocument context for this session:\n{context}"


def _welcome_message(language: str) -> str:
    messages = {
        "hi": "नमस्ते! मैं आपका SehatSaathi हूं। आपके दस्तावेज़ के बारे में कोई भी सवाल पूछ सकते हैं।",
        "en": "Hello! I'm your SehatSaathi. Feel free to ask me anything about your document.",
        "mr": "नमस्कार! मी तुमचा SehatSaathi आहे. तुमच्या कागदपत्राबद्दल काहीही विचारा.",
        "bn": "নমস্কার! আমি আপনার SehatSaathi। আপনার নথি সম্পর্কে যেকোনো প্রশ্ন জিজ্ঞেস করুন।",
        "ta": "வணக்கம்! நான் உங்கள் SehatSaathi. உங்கள் ஆவணம் பற்றி எதுவும் கேளுங்கள்.",
    }
    return messages.get(language, messages["en"])
