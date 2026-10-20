from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Option(StrictModel):
    key: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=300)


class Question(StrictModel):
    id: str = Field(min_length=1, max_length=40)
    type: Literal["single", "multiple", "judge"]
    stem: str = Field(min_length=1, max_length=300)
    options: list[Option] = Field(min_length=2, max_length=6)
    answer: list[str] = Field(min_length=1, max_length=6)
    explanation: str = Field(min_length=1, max_length=1200)
    knowledge_point: str = Field(min_length=1, max_length=100)
    difficulty: Literal["easy", "medium", "hard"]

    @model_validator(mode="after")
    def validate_options_and_answers(self):
        option_keys = [option.key for option in self.options]
        if len(option_keys) != len(set(option_keys)):
            raise ValueError("option keys must be unique")
        if len(self.answer) != len(set(self.answer)):
            raise ValueError("answer keys must be unique")
        if not set(self.answer).issubset(option_keys):
            raise ValueError("answers must reference existing options")
        if self.type in ("single", "judge") and len(self.answer) != 1:
            raise ValueError("single and judge questions require one answer")
        if self.type == "judge" and len(self.options) != 2:
            raise ValueError("judge questions require two options")
        if self.type == "multiple" and len(self.answer) < 2:
            raise ValueError("multiple questions require at least two answers")
        return self


class QuizContent(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=400)
    questions: list[Question] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_question_mix(self):
        question_ids = [question.id for question in self.questions]
        counts = {
            question_type: sum(
                question.type == question_type for question in self.questions
            )
            for question_type in ("single", "multiple", "judge")
        }
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("question ids must be unique")
        if counts != {"single": 3, "multiple": 1, "judge": 1}:
            raise ValueError("quiz must contain three single, one multiple, and one judge question")
        return self


class QuizGenerationOutput(QuizContent):
    pass


class Quiz(QuizContent):
    quiz_id: str = Field(min_length=1, max_length=64)
    source_type: Literal["text", "document", "web", "video"] = "text"
    user_input: str = Field(min_length=1, max_length=500)
