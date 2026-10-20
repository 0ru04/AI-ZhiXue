from pydantic import Field, field_validator

from app.models.quiz import StrictModel


class KnowledgePointsOutput(StrictModel):
    knowledge_points: list[str] = Field(min_length=1, max_length=10)

    @field_validator("knowledge_points")
    @classmethod
    def normalize_points(cls, values: list[str]) -> list[str]:
        points = [value.strip() for value in values]
        if (
            any(not point or len(point) > 80 for point in points)
            or len(set(points)) != len(points)
        ):
            raise ValueError("knowledge points must be unique and up to 80 chars")
        return points
