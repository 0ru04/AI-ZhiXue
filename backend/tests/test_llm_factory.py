import pytest
from langchain_core.runnables import RunnableLambda

import app.llm.factory as factory
from app.core.config import Settings
from app.core.exceptions import LLMConfigurationError
from app.models.report import ReportNarrative
from app.prompts.report_prompt import REPORT_PROMPT


class FakeModel:
    def __init__(self):
        self.schema = None
        self.method = None

    def with_structured_output(self, schema, *, method):
        self.schema = schema
        self.method = method
        return RunnableLambda(
            lambda _messages: {
                "three_line_summary": ["One.", "Two.", "Three."],
                "advice": ["Review."],
                "share_quote": "Keep learning.",
            }
        )


def test_factory_configures_deepseek_and_function_calling(monkeypatch):
    model = FakeModel()
    captured = {}
    monkeypatch.setattr(
        factory,
        "get_settings",
        lambda: Settings(
            deepseek_api_key="test-key",
            deepseek_model="deepseek-flash",
            deepseek_base_url="https://api.deepseek.com",
        ),
    )

    def make_model(**kwargs):
        captured.update(kwargs)
        return model

    monkeypatch.setattr(factory, "ChatOpenAI", make_model)
    chain = factory.create_structured_chain(ReportNarrative, REPORT_PROMPT, 0.5)
    output = chain.invoke(
        {
            "topic": "A topic",
            "quiz_json": "[]",
            "answer_records_json": "[]",
            "score_summary": "{}",
        }
    )

    assert output["share_quote"] == "Keep learning."
    assert captured["model"] == "deepseek-flash"
    assert captured["base_url"] == "https://api.deepseek.com"
    assert captured["api_key"] == "test-key"
    assert captured["max_retries"] == 0
    assert captured["extra_body"] == {"thinking": {"type": "disabled"}}
    assert model.schema is ReportNarrative
    assert model.method == "function_calling"


def test_factory_fails_explicitly_without_api_key(monkeypatch):
    monkeypatch.setattr(
        factory,
        "get_settings",
        lambda: Settings(_env_file=None),
    )
    monkeypatch.setattr(
        factory,
        "ChatOpenAI",
        lambda **_kwargs: pytest.fail("model must not be created without a key"),
    )

    with pytest.raises(LLMConfigurationError):
        factory.create_structured_chain(ReportNarrative, REPORT_PROMPT, 0.5)
