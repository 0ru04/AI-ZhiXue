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
from app.prompts.quiz_prompt import QUIZ_PROMPT, SOURCE_QUIZ_PROMPT
from app.services.live_knowledge_service import LiveKnowledgeService
from app.utils.content_filter import ensure_content_allowed


logger = logging.getLogger(__name__)


class QuizService:
    def __init__(
        self,
        settings: Settings,
        chain_factory: Callable = create_structured_chain,
        knowledge_service: LiveKnowledgeService | None = None,
    ) -> None:
        self.settings = settings
        self.chain_factory = chain_factory
        self.knowledge_service = knowledge_service

    async def generate(self, user_input: str) -> Quiz:
        clean_input = user_input.strip()
        knowledge_summary = None
        if self.knowledge_service is not None:
            knowledge_summary = await self.knowledge_service.get_knowledge_summary(
                clean_input
            )
        return await self._generate(
            content=clean_input,
            user_input=clean_input,
            source_type="text",
            knowledge_summary=knowledge_summary,
        )

    async def generate_from_source(
        self,
        *,
        source_type: str,
        title: str,
        content: str,
        knowledge_points: list[str],
    ) -> Quiz:
        clean_title = title.strip()
        clean_content = content.strip()
        clean_points = [point.strip() for point in knowledge_points if point.strip()]
        if not clean_title or not clean_content or not clean_points:
            raise ValueError("source title, content, and knowledge points are required")
        ensure_content_allowed(
            [clean_title, *clean_points],
            self.settings.blocked_terms,
        )
        source_label = {
            "document": "文档",
            "web": "网页",
            "video": "视频",
        }.get(source_type)
        if source_label is None:
            raise ValueError("unsupported source type")

        display_input = (
            f"{source_label}：{clean_title}\n知识点：{'、'.join(clean_points)}"
        )[:500]
        return await self._generate(
            content=clean_content,
            user_input=display_input,
            source_type=source_type,
            title=clean_title,
            knowledge_points=clean_points,
        )

    async def _generate(
        self,
        *,
        content: str,
        user_input: str,
        source_type: str,
        title: str | None = None,
        knowledge_points: list[str] | None = None,
        knowledge_summary: str | None = None,
    ) -> Quiz:
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("user_input must not be blank")
        ensure_content_allowed([clean_content], self.settings.blocked_terms)

        last_error: Exception | None = None
        for attempt in range(1, self.settings.llm_max_attempts + 1):
            try:
                prompt = SOURCE_QUIZ_PROMPT if knowledge_points else QUIZ_PROMPT
                chain = self.chain_factory(
                    QuizGenerationOutput,
                    prompt,
                    0.4,
                )
                chain_input = {"user_input": clean_content}
                if knowledge_points:
                    chain_input.update(
                        {
                            "title": title or "",
                            "knowledge_points": "、".join(knowledge_points),
                        }
                    )
                else:
                    chain_input["knowledge_summary"] = knowledge_summary or ""
                result = await chain.ainvoke(chain_input)
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
                    source_type=source_type,
                    user_input=user_input,
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
