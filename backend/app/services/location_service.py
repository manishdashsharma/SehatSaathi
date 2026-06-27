import httpx
import structlog

logger = structlog.get_logger(__name__)


async def reverse_geocode(lat: float, lng: float) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lng, "format": "json"},
                headers={"User-Agent": "SehatSaathi/1.0"},
            )
            data = response.json()
            address = data.get("address", {})
            return {
                "lat": lat,
                "lng": lng,
                "village": address.get("village") or address.get("town") or address.get("city"),
                "district": address.get("county") or address.get("district"),
                "state": address.get("state"),
            }
    except Exception as exc:
        logger.warning("reverse_geocode_failed", error=str(exc))
        return {"lat": lat, "lng": lng, "village": None, "district": None, "state": None}
