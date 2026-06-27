from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.core.dependencies import get_current_user
from app.core.exceptions import AppException
from app.schemas.user import RegisterRequest, RefreshRequest, LogoutRequest, TokenResponse, UserResponse
from app.services import auth_service
from app.utils.response_utils import error_response, success_response

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest) -> JSONResponse:
    try:
        result = await auth_service.register_or_login(
            phone=body.phone, name=body.name, language=body.language
        )
        user_resp = UserResponse.from_doc(result["user"])
        return success_response(
            TokenResponse(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                user=user_resp,
            ).model_dump(),
            status_code=200,
        )
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.post("/refresh")
async def refresh(body: RefreshRequest) -> JSONResponse:
    try:
        result = await auth_service.refresh_access_token(body.refresh_token)
        user_resp = UserResponse.from_doc(result["user"])
        return success_response(
            TokenResponse(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                user=user_resp,
            ).model_dump()
        )
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    await auth_service.revoke_refresh_token(current_user["_id"], body.refresh_token)
    return success_response({"message": "Logged out successfully"})
