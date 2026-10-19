from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import Field, field_validator

from app.api.dependencies import get_quiz_service
from app.models.quiz import StrictModel
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
):
    quiz = await service.generate(request.user_input)
    return {"code": 0, "message": "ok", "data": quiz.model_dump()}
