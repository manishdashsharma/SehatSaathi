from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel

EAgentType = Literal["diagnosis", "medication", "lifestyle", "risk"]


class AgentVerdictResponse(BaseModel):
    id: str
    document_id: str
    user_id: str
    agent_type: EAgentType
    verdict: dict[str, Any]
    passed_guardrail: bool
    created_at: datetime

    @classmethod
    def from_doc(cls, doc: dict) -> "AgentVerdictResponse":
        return cls(
            id=str(doc["_id"]),
            document_id=str(doc["document_id"]),
            user_id=str(doc["user_id"]),
            agent_type=doc["agent_type"],
            verdict=doc.get("verdict", {}),
            passed_guardrail=doc.get("passed_guardrail", True),
            created_at=doc["created_at"],
        )


class OrchestratorRequest(BaseModel):
    document_id: str


class OrchestratorResponse(BaseModel):
    document_id: str
    verdicts: list[AgentVerdictResponse]
    summary: str
