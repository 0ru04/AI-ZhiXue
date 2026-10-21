from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.api.dependencies import get_quiz_service, get_report_service
from app.core.config import Settings
from app.db.models import QuizGenerationTaskRow
from app.db.session import get_optional_db_session
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


def test_generate_quiz_creates_task_and_poll_returns_quiz(
    quiz: Quiz,
    task_database,
):
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_quiz_service] = lambda: FakeQuizService(quiz)
    app.dependency_overrides[get_optional_db_session] = task_database.dependency
    app.state.db_session_factory = task_database.session_factory

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/quiz/generate",
            json={"user_input": "Learn about RAG"},
        )
        assert created.status_code == 200
        task = created.json()["data"]
        assert task["status"] == "queued"
        assert task["task_id"]

        response = client.get(f"/api/v1/quiz/tasks/{task['task_id']}")

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert response.json()["data"]["status"] == "completed"
    assert response.json()["data"]["quiz"]["user_input"] == "Learn about RAG"


def test_generate_quiz_requires_database_for_persisted_tasks():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.post(
            "/api/v1/quiz/generate",
            json={"user_input": "Learn about RAG"},
        )

    assert response.status_code == 503
    assert response.json()["message"] == "出题任务需要配置数据库"


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


def test_ai_failure_is_reported_by_polling_task_status(task_database):
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_quiz_service] = FailingQuizService
    app.dependency_overrides[get_optional_db_session] = task_database.dependency
    app.state.db_session_factory = task_database.session_factory

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/quiz/generate",
            json={"user_input": "Learn about RAG"},
        )
        task_id = created.json()["data"]["task_id"]
        response = client.get(f"/api/v1/quiz/tasks/{task_id}")

    assert created.status_code == 200
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "failed"
    assert response.json()["data"]["error_message"] == (
        "AI 生成暂时失败，请稍后重试"
    )


def test_authenticated_task_results_are_not_readable_anonymously(task_database):
    task_database.tasks["private-task"] = QuizGenerationTaskRow(
        task_id="private-task",
        user_id=42,
        task_type="text",
        status="completed",
        request_json={"user_input": "private"},
        result_json=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_optional_db_session] = task_database.dependency

    with TestClient(app) as client:
        response = client.get("/api/v1/quiz/tasks/private-task")

    assert response.status_code == 404


def test_polling_marks_tasks_from_previous_server_process_as_failed(
    task_database,
):
    previous_time = datetime.now() - timedelta(minutes=1)
    task_database.tasks["interrupted-task"] = QuizGenerationTaskRow(
        task_id="interrupted-task",
        user_id=None,
        task_type="text",
        status="running",
        request_json={"user_input": "interrupted"},
        result_json=None,
        created_at=previous_time,
        updated_at=previous_time,
    )
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_optional_db_session] = task_database.dependency

    with TestClient(app) as client:
        response = client.get("/api/v1/quiz/tasks/interrupted-task")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "failed"
    assert response.json()["data"]["error_message"] == (
        "服务重启导致任务中断，请重新生成"
    )


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
