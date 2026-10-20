from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.models.quiz import StrictModel


class ParsedSourceResponse(StrictModel):
    source_type: Literal["document", "web", "video"]
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=30_000)
    headings: list[Annotated[str, Field(max_length=120)]] = Field(max_length=30)
    knowledge_points: list[Annotated[str, Field(max_length=80)]] = Field(
        min_length=1,
        max_length=10,
    )
    source_url: str | None = Field(default=None, max_length=2048)


class ParseUrlRequest(StrictModel):
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("url must not be blank")
        return value


class GenerateFromSourceRequest(StrictModel):
    source_type: Literal["document", "web", "video"]
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=30_000)
    headings: list[Annotated[str, Field(max_length=120)]] = Field(max_length=30)
    knowledge_points: list[Annotated[str, Field(max_length=80)]] = Field(
        min_length=1,
        max_length=10,
    )

    @field_validator("title", "content")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("knowledge_points")
    @classmethod
    def validate_knowledge_points(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized) or len(set(normalized)) != len(normalized):
            raise ValueError("knowledge points must be unique and non-empty")
        return normalized
