from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from app.core.dependencies import get_current_user, require_moderator_or_above
from app.core.exceptions import AppException
from app.schemas.user import (
    ConsentRequest,
    LocationUpdate,
    UpdateProfileRequest,
    UserResponse,
)
from app.services import user_service, location_service
from app.utils.response_utils import error_response, success_response

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/me/consent")
async def give_consent(
    body: ConsentRequest,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        user = await user_service.record_consent(str(current_user["_id"]), body.given)
        return success_response(UserResponse.from_doc(user).model_dump())
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.post("/me/profile")
async def update_profile(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        updates = body.model_dump(exclude_none=True)
        user = await user_service.update_profile(str(current_user["_id"]), updates)
        return success_response(UserResponse.from_doc(user).model_dump())
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.post("/me/location")
async def update_location(
    body: LocationUpdate,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        location = body.model_dump()
        if not location.get("village"):
            location = await location_service.reverse_geocode(body.lat, body.lng)
        user = await user_service.update_location(str(current_user["_id"]), location)
        return success_response(UserResponse.from_doc(user).model_dump())
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)) -> JSONResponse:
    return success_response(UserResponse.from_doc(current_user).model_dump())


@router.get("/")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    _admin: dict = Depends(require_moderator_or_above),
) -> JSONResponse:
    try:
        result = await user_service.list_users(page=page, limit=limit, role=role)
        result["items"] = [UserResponse.from_doc(u).model_dump() for u in result["items"]]
        return success_response(result)
    except AppException as exc:
        return error_response(exc.message, exc.status_code)
