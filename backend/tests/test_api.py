from fastapi.testclient import TestClient

from app.api.dependencies import get_quiz_service, get_report_service
from app.core.exceptions import AIProviderError
from app.main import create_app
from app.models.quiz import Quiz
from app.models.report import Report


class FakeQuizService:
    def __init__(self, quiz):
        self.quiz = quiz

    async def generate(self, user_input):
        return self.quiz.model_copy(update={"user_input": user_input})


class FakeReportService:
    async def generate(self, request):
        return Report(
            accuracy=80,
            correct_count=4,
            total_questions=5,
            xp_reward=80,
            coin_reward=12,
            max_streak=3,
            total_duration_ms=3000,
            mastered_points=["Basics"],
            weak_points=["Review"],
            three_line_summary=["One.", "Two.", "Three."],
            advice=["Review again."],
            share_quote="Keep learning.",
        )


class FailingQuizService:
    async def generate(self, user_input):
        raise AIProviderError()


def test_health_returns_standard_envelope():
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "ok",
        "data": {"status": "ok"},
    }


def test_h5_local_origin_allows_api_preflight():
    with TestClient(create_app()) as client:
        response = client.options(
            "/api/v1/quiz/generate",
            headers={
                "Origin": "http://localhost:10086",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:10086"
    )


def test_generate_quiz_returns_envelope_and_topic(quiz: Quiz):
    app = create_app()
    app.dependency_overrides[get_quiz_service] = lambda: FakeQuizService(quiz)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/quiz/generate",
            json={"user_input": "Learn about RAG"},
        )

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert response.json()["data"]["user_input"] == "Learn about RAG"


def test_generate_quiz_wraps_validation_errors_in_standard_envelope():
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/quiz/generate",
            json={"user_input": " "},
        )

    assert response.status_code == 422
    assert response.json() == {
        "code": 4220,
        "message": "请求参数有误",
        "data": None,
    }


def test_generate_quiz_rejects_input_over_500_characters():
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/quiz/generate",
            json={"user_input": "x" * 501},
        )

    assert response.status_code == 422
    assert response.json()["code"] == 4220


def test_ai_failure_uses_error_envelope():
    app = create_app()
    app.dependency_overrides[get_quiz_service] = FailingQuizService

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/quiz/generate",
            json={"user_input": "Learn about RAG"},
        )

    assert response.status_code == 502
    assert response.json() == {
        "code": 5001,
        "message": "AI 生成暂时失败，请稍后重试",
        "data": None,
    }


def test_generate_report_returns_standard_envelope(report_request):
    app = create_app()
    app.dependency_overrides[get_report_service] = FakeReportService

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/report/generate",
            json=report_request.model_dump(),
        )

    assert response.status_code == 200
    assert response.json()["data"]["accuracy"] == 80
