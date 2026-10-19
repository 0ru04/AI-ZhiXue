import json
import logging
from collections.abc import Callable

from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import (
    AIProviderError,
    ContentBlockedError,
    LLMConfigurationError,
)
from app.llm.factory import create_structured_chain
from app.models.report import Report, ReportNarrative, ReportRequest
from app.prompts.report_prompt import REPORT_PROMPT
from app.services.scoring_service import calculate_score
from app.utils.content_filter import ensure_content_allowed


logger = logging.getLogger(__name__)


class ReportService:
    def __init__(
        self,
        settings: Settings,
        chain_factory: Callable = create_structured_chain,
    ) -> None:
        self.settings = settings
        self.chain_factory = chain_factory

    async def generate(self, request: ReportRequest) -> Report:
        input_texts = [request.topic]
        for question in request.questions:
            input_texts.extend(
                [
                    question.stem,
                    question.explanation,
                    question.knowledge_point,
                    *(option.text for option in question.options),
                ]
            )
        ensure_content_allowed(input_texts, self.settings.blocked_terms)
        score = calculate_score(request)
        question_by_id = {question.id: question for question in request.questions}
        answers = []
        for record in request.answer_records:
            question = question_by_id[record.question_id]
            answers.append(
                {
                    "question_id": record.question_id,
                    "selected_answers": record.selected_answers,
                    "correct_answers": question.answer,
                    "is_correct": set(record.selected_answers) == set(question.answer),
                    "duration_ms": record.duration_ms,
                }
            )

        prompt_input = {
            "topic": request.topic,
            "quiz_json": json.dumps(
                [question.model_dump() for question in request.questions],
                ensure_ascii=False,
            ),
            "answer_records_json": json.dumps(answers, ensure_ascii=False),
            "score_summary": json.dumps(
                score.model_dump(
                    include={
                        "accuracy",
                        "correct_count",
                        "total_questions",
                        "xp_reward",
                        "coin_reward",
                        "mastered_points",
                        "weak_points",
                        "max_streak",
                    }
                ),
                ensure_ascii=False,
            ),
        }

        last_error: Exception | None = None
        for attempt in range(1, self.settings.llm_max_attempts + 1):
            try:
                chain = self.chain_factory(
                    ReportNarrative,
                    REPORT_PROMPT,
                    0.5,
                )
                narrative = ReportNarrative.model_validate(
                    await chain.ainvoke(prompt_input)
                )
                ensure_content_allowed(
                    [
                        *narrative.three_line_summary,
                        *narrative.advice,
                        narrative.share_quote,
                    ],
                    self.settings.blocked_terms,
                )
                return Report(
                    **score.model_dump(),
                    **narrative.model_dump(),
                )
            except (ContentBlockedError, LLMConfigurationError):
                raise
            except (ValidationError, ValueError) as error:
                last_error = error
                logger.warning(
                    "Report output validation failed on attempt %s/%s",
                    attempt,
                    self.settings.llm_max_attempts,
                    exc_info=True,
                )
            except Exception as error:
                last_error = error
                logger.exception(
                    "Report generation failed on attempt %s/%s",
                    attempt,
                    self.settings.llm_max_attempts,
                )

        raise AIProviderError() from last_error
