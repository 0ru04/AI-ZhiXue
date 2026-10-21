import asyncio
import json
import logging
from collections.abc import Callable
from typing import Literal

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.tools import StructuredTool
from langchain_tavily import TavilyExtract, TavilySearch
from langchain_tavily._utilities import (
    TavilyExtractAPIWrapper,
    TavilySearchAPIWrapper,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import Settings
from app.llm.factory import create_chat_model
from app.prompts.live_knowledge_prompt import LIVE_KNOWLEDGE_PROMPT
from app.services.source_import_service import validate_public_url
from app.utils.content_filter import ensure_content_allowed


logger = logging.getLogger(__name__)
MAX_CONTEXT_CHARS = 12_000
MIN_CONTEXT_CHARS = 200
MAX_URLS_PER_EXTRACTION = 3


class KnowledgeSummary(BaseModel):
    summary: str = Field(min_length=1, max_length=1200)
    key_points: list[str] = Field(min_length=3, max_length=8)

    @field_validator("key_points")
    @classmethod
    def validate_key_points(cls, points: list[str]) -> list[str]:
        if any(not point.strip() or len(point) > 80 for point in points):
            raise ValueError("key points must contain 1 to 80 characters")
        return points


class TavilySearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    search_depth: Literal["basic", "advanced"] = "basic"
    max_results: int | None = Field(default=None, ge=1, le=10)
    time_range: Literal["day", "week", "month", "year"] | None = None


class TavilyExtractInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urls: list[str] = Field(min_length=1, max_length=MAX_URLS_PER_EXTRACTION)
    query: str | None = Field(default=None, max_length=500)


class _ContextBudget:
    def __init__(self) -> None:
        self.used = 0

    def limit(self, content: str) -> str:
        remaining = MAX_CONTEXT_CHARS - self.used
        limited = content[:remaining]
        self.used += len(limited)
        return limited


class LiveKnowledgeService:
    def __init__(
        self,
        settings: Settings,
        *,
        model_factory: Callable = create_chat_model,
        agent_factory: Callable = create_agent,
        search_factory: Callable = TavilySearch,
        extract_factory: Callable = TavilyExtract,
    ) -> None:
        self.settings = settings
        self.model_factory = model_factory
        self.agent_factory = agent_factory
        self.search_factory = search_factory
        self.extract_factory = extract_factory

    async def get_knowledge_summary(self, user_input: str) -> str | None:
        api_key = self.settings.tavily_api_key
        if not self.settings.knowledge_agent_enabled or api_key is None:
            return None
        if not api_key.get_secret_value().strip():
            return None

        try:
            return await asyncio.wait_for(
                self._run_agent(user_input.strip()),
                timeout=self.settings.knowledge_agent_timeout_seconds,
            )
        except Exception as error:
            logger.warning(
                "Knowledge Agent failed; using original quiz input (%s)",
                type(error).__name__,
            )
            return None

    async def _run_agent(self, user_input: str) -> str | None:
        budget = _ContextBudget()
        tool_failed = False
        tavily_api_key = self.settings.tavily_api_key.get_secret_value()
        search_api = TavilySearchAPIWrapper(tavily_api_key=tavily_api_key)
        extract_api = TavilyExtractAPIWrapper(
            tavily_api_key=tavily_api_key
        )

        def limit_tool_result(result: object) -> str:
            nonlocal tool_failed
            if isinstance(result, dict) and result.get("error"):
                tool_failed = True
                return "联网工具暂时不可用。"
            return budget.limit(str(result))

        async def search(
            query: str,
            search_depth: Literal["basic", "advanced"] = "basic",
            max_results: int | None = None,
            time_range: Literal["day", "week", "month", "year"] | None = None,
        ) -> str:
            nonlocal tool_failed
            bounded_results = (
                self.settings.tavily_default_max_results
                if max_results is None
                else max_results
            )
            try:
                tool = self.search_factory(
                    api_wrapper=search_api,
                    max_results=bounded_results,
                    search_depth=search_depth,
                    time_range=time_range,
                    include_raw_content="markdown",
                    include_answer=False,
                    topic="general",
                )
                result = await asyncio.wait_for(
                    tool.ainvoke({"query": query}),
                    timeout=self.settings.tavily_tool_timeout_seconds,
                )
            except Exception:
                tool_failed = True
                return "联网搜索暂时不可用。"
            return limit_tool_result(result)

        async def extract(urls: list[str], query: str | None = None) -> str:
            nonlocal tool_failed
            for url in urls:
                validate_public_url(url)
            try:
                tool = self.extract_factory(
                    apiwrapper=extract_api,
                    extract_depth="advanced",
                    format="markdown",
                    include_images=False,
                    query=query,
                )
                result = await asyncio.wait_for(
                    tool.ainvoke({"urls": urls}),
                    timeout=self.settings.tavily_tool_timeout_seconds,
                )
            except Exception:
                tool_failed = True
                return "网页提取暂时不可用。"
            return limit_tool_result(result)

        tools = [
            StructuredTool.from_function(
                coroutine=search,
                name="tavily_search",
                description=(
                    "Search the public web for current information relevant to a "
                    "learning topic. Choose search depth, result count, and time range."
                ),
                args_schema=TavilySearchInput,
            ),
            StructuredTool.from_function(
                coroutine=extract,
                name="tavily_extract",
                description=(
                    "Extract readable content from one to three public HTTP or HTTPS "
                    "URLs. Provide the user's question as query when useful."
                ),
                args_schema=TavilyExtractInput,
            ),
        ]
        model = self.model_factory(self.settings, temperature=0.2)
        agent = self.agent_factory(
            model=model,
            tools=tools,
            system_prompt=LIVE_KNOWLEDGE_PROMPT,
            middleware=[
                ToolCallLimitMiddleware(
                    run_limit=self.settings.knowledge_agent_max_tool_calls,
                    exit_behavior="error",
                )
            ],
        )
        state = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]}
        )
        if tool_failed:
            logger.warning("Knowledge Agent tool failed; using original quiz input")
            return None
        if budget.used < MIN_CONTEXT_CHARS:
            logger.warning(
                "Knowledge Agent returned insufficient reference context; "
                "using original quiz input"
            )
            return None

        final_message = state["messages"][-1]
        content = final_message.content
        if not isinstance(content, str):
            content = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        result = KnowledgeSummary.model_validate(json.loads(content))
        ensure_content_allowed(
            [result.summary, *result.key_points],
            self.settings.blocked_terms,
        )
        return "\n".join(
            [
                result.summary,
                "关键点：",
                *(f"- {point}" for point in result.key_points),
            ]
        )
