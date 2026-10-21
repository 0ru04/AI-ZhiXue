from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.quiz import Quiz


class QuizGenerationTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    updated_at: datetime
    quiz: Quiz | None = None
    error_message: str | None = None
