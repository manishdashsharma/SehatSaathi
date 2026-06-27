import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_diagnosis_agent_returns_verdict():
    from app.agents.diagnosis_agent import DiagnosisAgent

    ocr_text = "Patient has high blood sugar. Fasting glucose 210 mg/dL."
    user_profile = {"language": "en", "_id": "123"}

    with patch.object(DiagnosisAgent, "_call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = '{"summary": "Elevated blood sugar noted.", "key_findings": ["High glucose"]}'
        with patch("app.services.guardrail_service.validate_response"):
            agent = DiagnosisAgent()
            result = await agent.run(ocr_text, user_profile)

    assert result["agent_type"] == "diagnosis"
    assert "verdict" in result
    assert result["passed_guardrail"] is True


@pytest.mark.asyncio
async def test_risk_agent_returns_urgency():
    from app.agents.risk_agent import RiskAgent

    with patch.object(RiskAgent, "_call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = '{"urgency_level": "high", "should_see_doctor": true, "urgency_reason": "High sugar."}'
        with patch("app.services.guardrail_service.validate_response"):
            agent = RiskAgent()
            result = await agent.run("High glucose 300 mg/dL", {"language": "en"})

    assert result["verdict"]["urgency_level"] == "high"
    assert result["verdict"]["should_see_doctor"] is True


@pytest.mark.asyncio
async def test_orchestrate_all_agents():
    from app.services.agent_orchestrator import orchestrate

    mock_doc = {
        "_id": "doc123",
        "user_id": "user123",
        "status": "processed",
        "ocr_text": "Blood pressure 140/90. Recommend rest.",
        "language": "en",
    }
    mock_user = {"_id": "user123", "language": "en"}

    with patch("app.services.agent_orchestrator.document_model.find_document_by_id") as mock_find:
        mock_find.return_value = mock_doc
        with patch("app.services.agent_orchestrator.verdict_model.bulk_create_verdicts") as mock_bulk:
            mock_bulk.return_value = []
            for agent_cls in ["DiagnosisAgent", "MedicationAgent", "LifestyleAgent", "RiskAgent"]:
                pass

            with patch("app.agents.diagnosis_agent.DiagnosisAgent.run", new_callable=AsyncMock) as d, \
                 patch("app.agents.medication_agent.MedicationAgent.run", new_callable=AsyncMock) as m, \
                 patch("app.agents.lifestyle_agent.LifestyleAgent.run", new_callable=AsyncMock) as l, \
                 patch("app.agents.risk_agent.RiskAgent.run", new_callable=AsyncMock) as r:

                d.return_value = {"agent_type": "diagnosis", "verdict": {}, "raw_response": "", "passed_guardrail": True}
                m.return_value = {"agent_type": "medication", "verdict": {}, "raw_response": "", "passed_guardrail": True}
                l.return_value = {"agent_type": "lifestyle", "verdict": {}, "raw_response": "", "passed_guardrail": True}
                r.return_value = {"agent_type": "risk", "verdict": {}, "raw_response": "", "passed_guardrail": True}
                mock_bulk.return_value = [d.return_value, m.return_value, l.return_value, r.return_value]

                result = await orchestrate("doc123", mock_user)

    assert len(result) == 4
