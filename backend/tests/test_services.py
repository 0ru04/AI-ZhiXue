import asyncio

import pytest

from app.core.config import Settings
from app.core.exceptions import AIProviderError, ContentBlockedError
from app.models.quiz import Quiz
from app.services.quiz_service import QuizService
from app.services.report_service import ReportService


class FakeChain:
    def __init__(self, result):
        self.result = result
        self.inputs = None

    async def ainvoke(self, inputs):
        self.inputs = inputs
        return self.result


class ChainFactory:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def __call__(self, schema, prompt, temperature):
        chain = FakeChain(self.results.pop(0))
        self.calls.append((schema, prompt, temperature, chain))
        return chain


def test_quiz_service_returns_valid_quiz_and_retries_bad_model_output(
    question_data, monkeypatch
):
    factory = ChainFactory(
        {"title": "", "summary": "", "questions": []},
        {
            "title": "A useful title",
            "summary": "A useful summary",
            "questions": question_data,
        },
    )
    service = QuizService(
        Settings(deepseek_api_key="test-key", content_blocklist=""),
        chain_factory=factory,
    )

    quiz = asyncio.run(service.generate(user_input="  Learn something  "))

    assert isinstance(quiz, Quiz)
    assert quiz.title == "A useful title"
    assert len(factory.calls) == 2
    assert factory.calls[-1][3].inputs["user_input"] == "Learn something"


def test_quiz_service_blocks_configured_terms_before_llm():
    factory = ChainFactory({"title": "unused"})
    service = QuizService(
        Settings(deepseek_api_key="test-key", content_blocklist="blocked term"),
        chain_factory=factory,
    )

    with pytest.raises(ContentBlockedError):
        asyncio.run(service.generate(user_input="This has a blocked term."))

    assert factory.calls == []


def test_quiz_service_blocks_unsafe_generated_content(question_data):
    question_data[0]["stem"] = "Contains a blocked phrase"
    factory = ChainFactory(
        {
            "title": "A useful title",
            "summary": "A useful summary",
            "questions": question_data,
        }
    )
    service = QuizService(
        Settings(
            deepseek_api_key="test-key",
            content_blocklist="blocked phrase",
        ),
        chain_factory=factory,
    )

    with pytest.raises(ContentBlockedError):
        asyncio.run(service.generate(user_input="Learn something"))

    assert len(factory.calls) == 1


def test_quiz_service_returns_error_after_retry_limit():
    factory = ChainFactory(
        {"title": "", "summary": "", "questions": []},
        {"title": "", "summary": "", "questions": []},
    )
    service = QuizService(
        Settings(deepseek_api_key="test-key", llm_max_attempts=2),
        chain_factory=factory,
    )

    with pytest.raises(AIProviderError):
        asyncio.run(service.generate(user_input="Learn something"))

    assert len(factory.calls) == 2


def test_quiz_service_generates_from_confirmed_source_points(question_data):
    factory = ChainFactory(
        {
            "title": "Rayleigh scattering",
            "summary": "The source explains the blue sky.",
            "questions": question_data,
        }
    )
    service = QuizService(
        Settings(deepseek_api_key="test-key", content_blocklist=""),
        chain_factory=factory,
    )

    quiz = asyncio.run(
        service.generate_from_source(
            source_type="web",
            title="Blue sky article",
            content="Air molecules scatter short wavelengths of visible light.",
            knowledge_points=["Rayleigh scattering"],
        )
    )

    assert quiz.source_type == "web"
    assert quiz.user_input.startswith("网页：Blue sky article")
    assert "Air molecules scatter" not in quiz.user_input
    assert factory.calls[0][3].inputs == {
        "user_input": "Air molecules scatter short wavelengths of visible light.",
        "title": "Blue sky article",
        "knowledge_points": "Rayleigh scattering",
    }


def test_quiz_service_blocks_unsafe_source_points_before_llm():
    factory = ChainFactory({"title": "unused"})
    service = QuizService(
        Settings(deepseek_api_key="test-key", content_blocklist="blocked phrase"),
        chain_factory=factory,
    )

    with pytest.raises(ContentBlockedError):
        asyncio.run(
            service.generate_from_source(
                source_type="document",
                title="Study notes",
                content="Safe content.",
                knowledge_points=["blocked phrase"],
            )
        )

    assert factory.calls == []


def test_report_service_generates_narrative_but_uses_server_calculated_score(
    report_request,
):
    factory = ChainFactory(
        {
            "three_line_summary": ["One.", "Two.", "Three."],
            "advice": ["Review applications."],
            "share_quote": "A useful quote.",
        }
    )
    service = ReportService(
        Settings(deepseek_api_key="test-key", content_blocklist=""),
        chain_factory=factory,
    )

    report = asyncio.run(service.generate(request=report_request))

    assert report.accuracy == 60
    assert report.mastered_points == ["Basics", "Review"]
    assert report.weak_points == ["Applications"]
    assert report.xp_reward == 70
    assert report.three_line_summary == ["One.", "Two.", "Three."]
    assert "accuracy" in factory.calls[0][3].inputs["score_summary"]


def test_report_service_blocks_unsafe_generated_narrative(report_request):
    factory = ChainFactory(
        {
            "three_line_summary": ["blocked phrase", "Two.", "Three."],
            "advice": ["Review applications."],
            "share_quote": "A useful quote.",
        }
    )
    service = ReportService(
        Settings(
            deepseek_api_key="test-key",
            content_blocklist="blocked phrase",
        ),
        chain_factory=factory,
    )

    with pytest.raises(ContentBlockedError):
        asyncio.run(service.generate(request=report_request))
