from typing import Annotated

from pydantic import Field, model_validator

from app.models.quiz import Question, StrictModel


class AnswerRecord(StrictModel):
    question_id: str = Field(min_length=1, max_length=40)
    selected_answers: list[str] = Field(min_length=1, max_length=6)
    is_correct: bool | None = None
    duration_ms: int = Field(ge=0, le=3_600_000)

    @model_validator(mode="after")
    def validate_selected_answers(self):
        if len(self.selected_answers) != len(set(self.selected_answers)):
            raise ValueError("selected answers must be unique")
        return self


class ReportRequest(StrictModel):
    quiz_id: str = Field(min_length=1, max_length=64)
    topic: str = Field(min_length=1, max_length=500)
    questions: list[Question] = Field(min_length=5, max_length=5)
    answer_records: list[AnswerRecord] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_answer_records(self):
        question_ids = [question.id for question in self.questions]
        answer_ids = [record.question_id for record in self.answer_records]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("question ids must be unique")
        if len(answer_ids) != len(set(answer_ids)):
            raise ValueError("answer records must be unique")
        if set(answer_ids) != set(question_ids):
            raise ValueError("every question must have exactly one answer record")

        answer_by_question = {
            record.question_id: record for record in self.answer_records
        }
        for question in self.questions:
            selected = answer_by_question[question.id].selected_answers
            option_keys = {option.key for option in question.options}
            if not set(selected).issubset(option_keys):
                raise ValueError("selected answers must reference existing options")
        return self


class ReportNarrative(StrictModel):
    three_line_summary: list[Annotated[str, Field(min_length=1, max_length=500)]] = (
        Field(min_length=3, max_length=3)
    )
    advice: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(
        min_length=1,
        max_length=3,
    )
    share_quote: str = Field(min_length=1, max_length=160)


class Score(StrictModel):
    accuracy: int = Field(ge=0, le=100)
    correct_count: int = Field(ge=0, le=5)
    total_questions: int = Field(ge=1, le=5)
    xp_reward: int = Field(ge=0)
    coin_reward: int = Field(ge=0)
    max_streak: int = Field(ge=0)
    total_duration_ms: int = Field(ge=0)
    mastered_points: list[str]
    weak_points: list[str]


class Report(Score, ReportNarrative):
    pass
