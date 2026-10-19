import logging
from collections.abc import Callable
from uuid import uuid4

from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import (
    AIProviderError,
    APIError,
    ContentBlockedError,
    LLMConfigurationError,
)
from app.llm.factory import create_structured_chain
from app.models.quiz import Quiz, QuizGenerationOutput
from app.prompts.quiz_prompt import QUIZ_PROMPT
from app.utils.content_filter import ensure_content_allowed


logger = logging.getLogger(__name__)


class QuizService:
    def __init__(
        self,
        settings: Settings,
        chain_factory: Callable = create_structured_chain,
    ) -> None:
        self.settings = settings
        self.chain_factory = chain_factory

    async def generate(self, user_input: str) -> Quiz:
        clean_input = user_input.strip()
        ensure_content_allowed([clean_input], self.settings.blocked_terms)

        last_error: Exception | None = None
        for attempt in range(1, self.settings.llm_max_attempts + 1):
            try:
                chain = self.chain_factory(
                    QuizGenerationOutput,
                    QUIZ_PROMPT,
                    0.4,
                )
                result = await chain.ainvoke({"user_input": clean_input})
                content = QuizGenerationOutput.model_validate(result)
                texts = [content.title, content.summary]
                for question in content.questions:
                    texts.extend(
                        [
                            question.stem,
                            question.explanation,
                            question.knowledge_point,
                            *(option.text for option in question.options),
                        ]
                    )
                ensure_content_allowed(texts, self.settings.blocked_terms)
                return Quiz(
                    quiz_id=f"quiz_{uuid4().hex[:12]}",
                    source_type="text",
                    user_input=clean_input,
                    **content.model_dump(),
                )
            except (ContentBlockedError, LLMConfigurationError):
                raise
            except (ValidationError, ValueError) as error:
                last_error = error
                logger.warning(
                    "Quiz output validation failed on attempt %s/%s",
                    attempt,
                    self.settings.llm_max_attempts,
                    exc_info=True,
                )
            except Exception as error:
                last_error = error
                logger.exception(
                    "Quiz generation failed on attempt %s/%s",
                    attempt,
                    self.settings.llm_max_attempts,
                )

        raise AIProviderError() from last_error
