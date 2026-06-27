from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse
from app.core.dependencies import get_current_user
from app.core.exceptions import AppException
from app.schemas.document import DocumentResponse
from app.services import document_service
from app.utils.response_utils import error_response, success_response

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        doc = await document_service.upload_document(current_user, file)
        return success_response(DocumentResponse.from_doc(doc).model_dump(), status_code=201)
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.get("/")
async def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        result = await document_service.list_documents(
            str(current_user["_id"]), page=page, limit=limit
        )
        result["items"] = [DocumentResponse.from_doc(d).model_dump() for d in result["items"]]
        return success_response(result)
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        doc = await document_service.get_document(document_id, str(current_user["_id"]))
        return success_response(DocumentResponse.from_doc(doc).model_dump())
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.get("/{document_id}/url")
async def get_document_url(
    document_id: str,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        url = await document_service.get_presigned_url(document_id, str(current_user["_id"]))
        return success_response({"url": url})
    except AppException as exc:
        return error_response(exc.message, exc.status_code)
