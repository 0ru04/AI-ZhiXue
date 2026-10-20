from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_dependencies import get_optional_current_user
from app.api.dependencies import get_quiz_service
from app.core.exceptions import UserSystemConfigurationError
from app.db.models import User
from app.db.session import get_optional_db_session
from app.models.quiz import StrictModel
from app.services.persistence_service import PersistenceService
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
    service: Annotated[QuizService, Depends(get_quiz_service)],
    user: Annotated[User | None, Depends(get_optional_current_user)],
    session: Annotated[AsyncSession | None, Depends(get_optional_db_session)],
):
    quiz = await service.generate(request.user_input)
    if user is not None:
        if session is None:
            raise UserSystemConfigurationError("用户数据库尚未配置")
        await PersistenceService().save_quiz(session, user, quiz)
    return {"code": 0, "message": "ok", "data": quiz.model_dump()}
