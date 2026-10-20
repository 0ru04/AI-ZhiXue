from typing import Any

from pydantic import AnyHttpUrl, Field, model_validator

from app.models.quiz import StrictModel


class LoginRequest(StrictModel):
    code: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_code(self):
        self.code = self.code.strip()
        if not self.code:
            raise ValueError("code must not be blank")
        return self


class UserSummary(StrictModel):
    id: int
    nickname: str
    avatar_url: str | None
    total_xp: int


class LoginResponse(StrictModel):
    token: str
    user: UserSummary


class UserProfile(UserSummary):
    quiz_count: int
    correct_count: int
    average_accuracy: float


class UserProfileUpdate(StrictModel):
    nickname: str | None = Field(default=None, max_length=100)
    avatar_url: AnyHttpUrl | None = None

    @model_validator(mode="after")
    def validate_profile_update(self):
        if not self.model_fields_set:
            raise ValueError("at least one profile field is required")
        if "nickname" in self.model_fields_set:
            if self.nickname is None:
                raise ValueError("nickname must not be null")
            self.nickname = self.nickname.strip()
            if not self.nickname:
                raise ValueError("nickname must not be blank")
        return self


class QuizHistoryItem(StrictModel):
    quiz_id: str
    title: str
    accuracy: float
    question_count: int
    created_at: str


class QuizHistoryPage(StrictModel):
    items: list[QuizHistoryItem]
    total: int
    page: int
    page_size: int


class QuizHistoryDetail(StrictModel):
    quiz_id: str
    title: str
    summary: str | None
    user_input: str
    questions: list[dict[str, Any]]
    answer_records: list[dict[str, Any]]
    report: dict[str, Any]
    created_at: str
