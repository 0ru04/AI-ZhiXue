import asyncio
import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from app.core.config import Settings
from app.prompts.live_knowledge_prompt import LIVE_KNOWLEDGE_PROMPT
from app.services import live_knowledge_service
from app.services.live_knowledge_service import (
    LiveKnowledgeService,
    KnowledgeSummary,
    TavilySearchInput,
    _ContextBudget,
)


VALID_SUMMARY = json.dumps(
    {
        "summary": "A concise summary of the retrieved learning material.",
        "key_points": ["Key point one", "Key point two", "Key point three"],
    }
)


def test_live_knowledge_prompt_handles_ambiguous_terms():
    assert "不同领域含义不同" in LIVE_KNOWLEDGE_PROMPT
    assert "比较主要含义" in LIVE_KNOWLEDGE_PROMPT


class ToolCallingFakeModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


class FakeTavilyTool:
    def __init__(self, result="x" * 250):
        self.result = result
        self.input = None

    async def ainvoke(self, tool_input):
        self.input = tool_input
        return self.result


def make_service(
    responses,
    *,
    search_factory=None,
    extract_factory=None,
    agent_factory=None,
    settings=None,
):
    model = ToolCallingFakeModel(responses=responses)
    kwargs = {}
    if agent_factory is not None:
        kwargs["agent_factory"] = agent_factory
    return LiveKnowledgeService(
        settings or Settings(_env_file=None, tavily_api_key="test-key"),
        model_factory=lambda *_args, **_kwargs: model,
        search_factory=search_factory or (lambda **_kwargs: FakeTavilyTool()),
        extract_factory=extract_factory or (lambda **_kwargs: FakeTavilyTool()),
        **kwargs,
    )


def tool_call(name, args, call_id="tool-call"):
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": name,
                "args": args,
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def test_agent_search_returns_summary_and_uses_dynamic_parameters():
    search_config = {}

    def search_factory(**kwargs):
        search_config.update(kwargs)
        return FakeTavilyTool()

    service = make_service(
        [
            tool_call(
                "tavily_search",
                {
                    "query": "recent plant science",
                    "search_depth": "advanced",
                    "max_results": 8,
                    "time_range": "month",
                },
            ),
            AIMessage(content=VALID_SUMMARY),
        ],
        search_factory=search_factory,
    )

    summary = asyncio.run(service.get_knowledge_summary("plant science"))

    assert summary is not None
    assert "A concise summary" in summary
    assert search_config["max_results"] == 8
    assert search_config["search_depth"] == "advanced"
    assert search_config["time_range"] == "month"


def test_agent_search_uses_configured_default_result_count():
    search_config = {}
    service = make_service(
        [
            tool_call("tavily_search", {"query": "a topic"}),
            AIMessage(content=VALID_SUMMARY),
        ],
        search_factory=lambda **kwargs: (
            search_config.update(kwargs) or FakeTavilyTool()
        ),
        settings=Settings(
            _env_file=None,
            tavily_api_key="test-key",
            tavily_default_max_results=7,
        ),
    )

    asyncio.run(service.get_knowledge_summary("a topic"))

    assert search_config["max_results"] == 7


def test_tavily_wrappers_receive_unwrapped_configured_key(monkeypatch):
    wrapper_keys = []

    class FakeAPIWrapper:
        def __init__(self, *, tavily_api_key):
            wrapper_keys.append(tavily_api_key)

    monkeypatch.setattr(
        live_knowledge_service,
        "TavilySearchAPIWrapper",
        FakeAPIWrapper,
    )
    monkeypatch.setattr(
        live_knowledge_service,
        "TavilyExtractAPIWrapper",
        FakeAPIWrapper,
    )
    service = make_service(
        [
            tool_call("tavily_search", {"query": "a topic"}),
            AIMessage(content=VALID_SUMMARY),
        ],
        settings=Settings(
            _env_file=None,
            tavily_api_key="fake-test-key",
        ),
    )

    asyncio.run(service.get_knowledge_summary("a topic"))

    assert wrapper_keys == ["fake-test-key", "fake-test-key"]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/private",
        "https://" + "user" + ":" + "pass" + "@example.com/page",
        "not-a-url",
    ],
)
def test_agent_rejects_unsafe_url_before_tavily_extract(url):
    extract_calls = []
    service = make_service(
        [
            tool_call(
                "tavily_extract",
                {"urls": [url]},
            ),
            AIMessage(content=VALID_SUMMARY),
        ],
        extract_factory=lambda **kwargs: (
            extract_calls.append(kwargs) or FakeTavilyTool()
        ),
    )

    assert asyncio.run(
        service.get_knowledge_summary("extract this page")
    ) is None
    assert extract_calls == []


def test_agent_times_out_tool_call_and_returns_no_summary():
    class SlowTool(FakeTavilyTool):
        async def ainvoke(self, _tool_input):
            await asyncio.sleep(1)
            return "late result"

    service = make_service(
        [
            tool_call("tavily_search", {"query": "a topic"}),
            AIMessage(content=VALID_SUMMARY),
        ],
        search_factory=lambda **_kwargs: SlowTool(),
        settings=Settings(
            _env_file=None,
            tavily_api_key="test-key",
            tavily_tool_timeout_seconds=0.01,
        ),
    )

    assert asyncio.run(service.get_knowledge_summary("a topic")) is None


def test_agent_skips_when_disabled_or_tavily_key_missing():
    for settings in (
        Settings(_env_file=None, knowledge_agent_enabled=False),
        Settings(_env_file=None),
    ):
        service = make_service(
            [],
            settings=settings,
        )

        assert asyncio.run(service.get_knowledge_summary("a topic")) is None


@pytest.mark.parametrize(
    "max_results",
    [0, 11],
)
def test_search_tool_rejects_result_counts_outside_supported_range(max_results):
    with pytest.raises(ValidationError):
        TavilySearchInput(query="a topic", max_results=max_results)


def test_search_tool_defaults_optional_agent_parameters():
    params = TavilySearchInput(query="a topic")

    assert params.search_depth == "basic"
    assert params.max_results is None
    assert params.time_range is None


def test_agent_stops_after_configured_tool_call_limit():
    search_calls = []
    service = make_service(
        [
            tool_call(
                "tavily_search",
                {"query": "first search"},
                call_id="first-search",
            ),
            tool_call(
                "tavily_search",
                {"query": "second search"},
                call_id="second-search",
            ),
            AIMessage(content=VALID_SUMMARY),
        ],
        search_factory=lambda **kwargs: (
            search_calls.append(kwargs) or FakeTavilyTool()
        ),
        settings=Settings(
            _env_file=None,
            tavily_api_key="test-key",
            knowledge_agent_max_tool_calls=1,
        ),
    )

    assert asyncio.run(service.get_knowledge_summary("a topic")) is None
    assert len(search_calls) == 1


def test_agent_total_timeout_returns_no_summary():
    class SlowAgent:
        async def ainvoke(self, _input):
            await asyncio.sleep(1)

    service = make_service(
        [],
        agent_factory=lambda **_kwargs: SlowAgent(),
        settings=Settings(
            _env_file=None,
            tavily_api_key="test-key",
            knowledge_agent_timeout_seconds=0.01,
        ),
    )

    assert asyncio.run(service.get_knowledge_summary("a topic")) is None


def test_agent_failure_log_does_not_include_exception_message(caplog):
    class FailingAgent:
        async def ainvoke(self, _input):
            raise RuntimeError("sensitive body and api secret")

    service = make_service(
        [],
        agent_factory=lambda **_kwargs: FailingAgent(),
    )

    assert asyncio.run(service.get_knowledge_summary("a topic")) is None
    assert "sensitive body and api secret" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_tavily_error_response_falls_back_without_logging_error_body(caplog):
    service = make_service(
        [
            tool_call("tavily_search", {"query": "a topic"}),
            AIMessage(content=VALID_SUMMARY),
        ],
        search_factory=lambda **_kwargs: FakeTavilyTool(
            result={"error": "sensitive provider response"}
        ),
    )

    assert asyncio.run(service.get_knowledge_summary("a topic")) is None
    assert "Knowledge Agent tool failed" in caplog.text
    assert "sensitive provider response" not in caplog.text


def test_context_budget_caps_combined_tool_results():
    budget = _ContextBudget()

    first = budget.limit("a" * 8000)
    second = budget.limit("b" * 8000)

    assert len(first) + len(second) == 12_000
    assert second == "b" * 4000


def test_agent_rejects_tool_context_shorter_than_minimum():
    service = make_service(
        [
            tool_call("tavily_search", {"query": "a topic"}),
            AIMessage(content=VALID_SUMMARY),
        ],
        search_factory=lambda **_kwargs: FakeTavilyTool(result="x" * 199),
    )

    assert asyncio.run(service.get_knowledge_summary("a topic")) is None


@pytest.mark.parametrize(
    "data",
    [
        {"summary": "", "key_points": ["one", "two", "three"]},
        {"summary": "valid", "key_points": ["one", "two"]},
        {
            "summary": "valid",
            "key_points": ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"],
        },
        {"summary": "valid", "key_points": ["a" * 81, "two", "three"]},
        {"summary": "s" * 1201, "key_points": ["one", "two", "three"]},
    ],
)
def test_knowledge_summary_rejects_invalid_lengths_and_point_counts(data):
    with pytest.raises(ValidationError):
        KnowledgeSummary.model_validate(data)


def test_agent_rejects_empty_or_invalid_summary_after_search():
    for response in (
        '{"summary":"","key_points":[]}',
        '{"summary":"valid","key_points":["one","two"]}',
        "not json",
    ):
        service = make_service(
            [
                tool_call("tavily_search", {"query": "a topic"}),
                AIMessage(content=response),
            ]
        )

        assert asyncio.run(service.get_knowledge_summary("a topic")) is None


def test_agent_filters_blocked_words_from_summary():
    blocked_summary = json.dumps(
        {
            "summary": "A blocked reference.",
            "key_points": ["Key one", "Key two", "Key three"],
        }
    )
    service = make_service(
        [
            tool_call("tavily_search", {"query": "a topic"}),
            AIMessage(content=blocked_summary),
        ],
        settings=Settings(
            _env_file=None,
            tavily_api_key="test-key",
            content_blocklist="blocked",
        ),
    )

    assert asyncio.run(service.get_knowledge_summary("a topic")) is None
