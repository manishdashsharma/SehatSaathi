import asyncio
from app.agents.diagnosis_agent import DiagnosisAgent
from app.agents.medication_agent import MedicationAgent
from app.agents.lifestyle_agent import LifestyleAgent
from app.agents.risk_agent import RiskAgent
from app.core.exceptions import NotFoundError
from app.models import agent_verdict as verdict_model
from app.models import document as document_model
import structlog

logger = structlog.get_logger(__name__)

_agents = [DiagnosisAgent, MedicationAgent, LifestyleAgent, RiskAgent]


async def orchestrate(document_id: str, user: dict) -> list[dict]:
    doc = await document_model.find_document_by_id(document_id)
    if not doc:
        raise NotFoundError("Document")

    if doc["status"] != "processed" or not doc.get("ocr_text"):
        raise ValueError("Document has not been processed yet. Please wait and retry.")

    user_id = str(user["_id"])
    ocr_text = doc["ocr_text"]

    results = await asyncio.gather(
        *[agent_cls().run(ocr_text, user) for agent_cls in _agents],
        return_exceptions=True,
    )

    successful_verdicts = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("agent_failed", error=str(result))
            continue
        successful_verdicts.append(result)

    if not successful_verdicts:
        raise RuntimeError("All agents failed to process the document")

    stored = await verdict_model.bulk_create_verdicts([
        {
            **v,
            "document_id": document_id,
            "user_id": user_id,
        }
        for v in successful_verdicts
    ])

    logger.info(
        "orchestration_complete",
        document_id=document_id,
        agent_count=len(stored),
    )
    return stored


async def get_verdicts(document_id: str) -> list[dict]:
    return await verdict_model.find_verdicts_by_document(document_id)
