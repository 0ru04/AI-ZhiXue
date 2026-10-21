from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_dependencies import get_optional_current_user
from app.api.dependencies import get_quiz_service
from app.core.exceptions import UserSystemConfigurationError
from app.db.models import User
from app.db.session import get_optional_db_session
from app.models.quiz import StrictModel
from app.models.quiz_task import QuizGenerationTask
from app.services.quiz_generation_task_service import (
    create_quiz_generation_task,
    execute_quiz_generation_task,
    get_quiz_generation_task,
    task_response,
)
from app.services.quiz_service import QuizService


router = APIRouter()


class QuizGenerateRequest(StrictModel):
    user_input: str = Field(min_length=1, max_length=500)

    @field_validator("user_input")
    @classmethod
    def normalize_user_input(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("user_input must not be blank")
        return value


@router.post("/quiz/generate")
async def generate_quiz(
    request: QuizGenerateRequest,
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
        task_type="text",
        request_data={"user_input": request.user_input},
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


@router.get("/quiz/tasks/{task_id}")
async def get_quiz_task(
    task_id: str,
    user: Annotated[User | None, Depends(get_optional_current_user)],
    session: Annotated[AsyncSession | None, Depends(get_optional_db_session)],
    http_request: Request,
):
    if session is None:
        raise UserSystemConfigurationError("出题任务需要配置数据库")
    task: QuizGenerationTask = await get_quiz_generation_task(
        session,
        task_id,
        user.id if user is not None else None,
        http_request.app.state.started_at,
    )
    return {"code": 0, "message": "ok", "data": task.model_dump(mode="json")}
