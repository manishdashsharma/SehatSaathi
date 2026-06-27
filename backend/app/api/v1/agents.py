from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.core.dependencies import get_current_user
from app.core.exceptions import AppException
from app.schemas.agent import AgentVerdictResponse, OrchestratorRequest, OrchestratorResponse
from app.services import agent_orchestrator
from app.utils.response_utils import error_response, success_response
import structlog

router = APIRouter(prefix="/agents", tags=["agents"])
logger = structlog.get_logger(__name__)


@router.post("/analyze")
async def analyze_document(
    body: OrchestratorRequest,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        verdicts = await agent_orchestrator.orchestrate(body.document_id, current_user)
        verdict_responses = [AgentVerdictResponse.from_doc(v).model_dump() for v in verdicts]

        summary_parts = []
        for v in verdicts:
            if v.get("agent_type") == "diagnosis":
                summary_parts.append(v["verdict"].get("summary", ""))

        return success_response(
            OrchestratorResponse(
                document_id=body.document_id,
                verdicts=verdict_responses,
                summary=" ".join(summary_parts).strip(),
            ).model_dump()
        )
    except AppException as exc:
        return error_response(exc.message, exc.status_code)
    except ValueError as exc:
        return error_response(str(exc), 400)
    except RuntimeError as exc:
        return error_response(str(exc), 500)


@router.get("/{document_id}/verdicts")
async def get_verdicts(
    document_id: str,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        verdicts = await agent_orchestrator.get_verdicts(document_id)
        return success_response([AgentVerdictResponse.from_doc(v).model_dump() for v in verdicts])
    except AppException as exc:
        return error_response(exc.message, exc.status_code)
