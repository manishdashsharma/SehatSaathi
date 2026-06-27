import structlog

logger = structlog.get_logger(__name__)


async def send_emergency_alert(
    doctor_email: str,
    doctor_name: str,
    patient_name: str,
    patient_phone: str,
    session_id: str,
    emergency_score: float,
    transcript_excerpt: str,
) -> dict:
    logger.info(
        "emergency_alert_stub",
        doctor_email=doctor_email,
        patient_phone=patient_phone,
        session_id=session_id,
        emergency_score=emergency_score,
    )
    return {"sent": True, "to": doctor_email}
