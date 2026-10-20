from typing import Annotated
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_dependencies import get_optional_current_user
from app.api.dependencies import get_quiz_service, get_source_import_service
from app.core.exceptions import SourceImportError, UserSystemConfigurationError
from app.db.models import User
from app.db.session import get_optional_db_session
from app.models.source_import import (
    GenerateFromSourceRequest,
    ParseUrlRequest,
    ParsedSourceResponse,
)
from app.services.persistence_service import PersistenceService
from app.services.quiz_service import QuizService
from app.services.source_import_service import MAX_UPLOAD_BYTES, SourceImportService


router = APIRouter(prefix="/source")


@router.post("/parse/document")
async def parse_document(
    file: Annotated[UploadFile, File()],
    service: Annotated[SourceImportService, Depends(get_source_import_service)],
    file_name: Annotated[str | None, Form()] = None,
):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise SourceImportError("单个文件不能超过 20MB", status_code=413)
    filename = file.filename or ""
    if not PurePath(filename.replace("\\", "/")).suffix:
        filename = file_name or filename
    parsed = await service.parse_document(filename, content)
    response = ParsedSourceResponse(**parsed.__dict__)
    return {"code": 0, "message": "ok", "data": response.model_dump()}


@router.post("/parse/url")
async def parse_url(
    request: ParseUrlRequest,
    service: Annotated[SourceImportService, Depends(get_source_import_service)],
):
    parsed = await service.parse_url(request.url)
    response = ParsedSourceResponse(**parsed.__dict__)
    return {"code": 0, "message": "ok", "data": response.model_dump()}


@router.post("/generate")
async def generate_from_source(
    request: GenerateFromSourceRequest,
    service: Annotated[QuizService, Depends(get_quiz_service)],
    user: Annotated[User | None, Depends(get_optional_current_user)],
    session: Annotated[AsyncSession | None, Depends(get_optional_db_session)],
):
    quiz = await service.generate_from_source(
        source_type=request.source_type,
        title=request.title,
        content=request.content,
        knowledge_points=request.knowledge_points,
    )
    if user is not None:
        if session is None:
            raise UserSystemConfigurationError("用户数据库尚未配置")
        await PersistenceService().save_quiz(session, user, quiz)
    return {"code": 0, "message": "ok", "data": quiz.model_dump()}
