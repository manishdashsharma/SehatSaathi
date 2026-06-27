from typing import Any
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(data: Any = None, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "data": jsonable_encoder(data), "error": None},
    )


def error_response(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "data": None, "error": message},
    )


def paginated_response(
    items: list,
    total: int,
    page: int,
    limit: int,
    serializer=None,
) -> dict:
    serialized = [serializer.from_doc(i).model_dump() for i in items] if serializer else items
    skip = (page - 1) * limit
    return {
        "items": serialized,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "has_next_page": skip + len(items) < total,
        },
    }
