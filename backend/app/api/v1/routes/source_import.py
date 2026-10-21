from typing import Annotated
from pathlib import PurePath

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
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
from app.services.quiz_generation_task_service import (
    create_quiz_generation_task,
    execute_quiz_generation_task,
    task_response,
)
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
    http_request: Request,
    background_tasks: BackgroundTasks,
    service: Annotated[QuizService, Depends(get_quiz_service)],
    user: Annotated[User | None, Depends(get_optional_current_user)],
    session: Annotated[AsyncSession | None, Depends(get_optional_db_session)],
):
    if session is None:
        raise UserSystemConfigurationError("出题任务需要配置数据库")
    session_factory = getattr(http_request.app.state, "db_session_factory", None)
    if session_factory is None:
        raise UserSystemConfigurationError("出题任务数据库尚未配置")
    task = await create_quiz_generation_task(
        session,
        task_type="source",
        request_data=request.model_dump(mode="json"),
        user_id=user.id if user is not None else None,
        server_started_at=http_request.app.state.started_at,
    )
    background_tasks.add_task(
        execute_quiz_generation_task,
        task.task_id,
        session_factory,
        service,
    )
    return {
        "code": 0,
        "message": "ok",
        "data": task_response(task).model_dump(mode="json"),
    }
