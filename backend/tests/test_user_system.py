from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.dependencies import get_quiz_service, get_report_service
from app.api.v1.routes.user import get_wechat_login_provider
from app.core.config import get_settings
from app.main import create_app
from app.models.report import Report
from app.models.quiz import Quiz


class FakeWechatLoginProvider:
    async def exchange_code(self, code: str) -> str:
        return f"openid-{code}"


class FakeQuizService:
    async def generate(self, user_input: str) -> Quiz:
        return Quiz(
            quiz_id=f"quiz_{uuid4().hex}",
            title="测试题库",
            summary="用户系统集成测试",
            source_type="text",
            user_input=user_input,
            questions=[
                {
                    "id": "q1",
                    "type": "single",
                    "stem": "题目一",
                    "options": [
                        {"key": "A", "text": "正确"},
                        {"key": "B", "text": "错误"},
                    ],
                    "answer": ["A"],
                    "explanation": "A 正确",
                    "knowledge_point": "测试知识点",
                    "difficulty": "easy",
                },
                {
                    "id": "q2",
                    "type": "single",
                    "stem": "题目二",
                    "options": [
                        {"key": "A", "text": "正确"},
                        {"key": "B", "text": "错误"},
                    ],
                    "answer": ["A"],
                    "explanation": "A 正确",
                    "knowledge_point": "测试知识点",
                    "difficulty": "easy",
                },
                {
                    "id": "q3",
                    "type": "single",
                    "stem": "题目三",
                    "options": [
                        {"key": "A", "text": "正确"},
                        {"key": "B", "text": "错误"},
                    ],
                    "answer": ["A"],
                    "explanation": "A 正确",
                    "knowledge_point": "测试知识点",
                    "difficulty": "easy",
                },
                {
                    "id": "q4",
                    "type": "multiple",
                    "stem": "题目四",
                    "options": [
                        {"key": "A", "text": "正确一"},
                        {"key": "B", "text": "正确二"},
                        {"key": "C", "text": "错误"},
                    ],
                    "answer": ["A", "B"],
                    "explanation": "A 和 B 正确",
                    "knowledge_point": "测试知识点",
                    "difficulty": "medium",
                },
                {
                    "id": "q5",
                    "type": "judge",
                    "stem": "题目五",
                    "options": [
                        {"key": "A", "text": "正确"},
                        {"key": "B", "text": "错误"},
                    ],
                    "answer": ["A"],
                    "explanation": "A 正确",
                    "knowledge_point": "测试知识点",
                    "difficulty": "easy",
                },
            ],
        )


class FakeReportService:
    async def generate(self, request):
        return Report(
            accuracy=80,
            correct_count=4,
            total_questions=5,
            xp_reward=86,
            coin_reward=12,
            max_streak=3,
            total_duration_ms=5000,
            mastered_points=["测试知识点"],
            weak_points=[],
            three_line_summary=["总结一", "总结二", "总结三"],
            advice=["复习建议"],
            share_quote="继续学习",
        )


@pytest.fixture
def client():
    settings = get_settings()
    assert settings.test_database_url is not None
    test_url = settings.test_database_url.get_secret_value()
    if test_url.startswith("mysql+pymysql://"):
        test_url = test_url.replace(
            "mysql+pymysql://", "mysql+asyncmy://", 1
        )
    test_settings = settings.model_copy(
        update={
            "database_url": SecretStr(test_url),
            "jwt_secret_key": SecretStr("test-only-jwt-secret-that-is-long-enough"),
        }
    )
    app = create_app(test_settings)
    app.dependency_overrides[get_wechat_login_provider] = (
        FakeWechatLoginProvider
    )
    app.dependency_overrides[get_quiz_service] = FakeQuizService
    app.dependency_overrides[get_report_service] = FakeReportService
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient) -> tuple[str, dict]:
    code = uuid4().hex
    response = client.post("/api/v1/user/login", json={"code": code})
    assert response.status_code == 200
    assert response.json()["code"] == 0
    data = response.json()["data"]
    return data["token"], data["user"]


def generate_quiz(client: TestClient, user_input: str, headers=None) -> dict:
    response = client.post(
        "/api/v1/quiz/generate",
        headers=headers,
        json={"user_input": user_input},
    )
    assert response.status_code == 200
    task_id = response.json()["data"]["task_id"]
    result = client.get(f"/api/v1/quiz/tasks/{task_id}", headers=headers)
    assert result.status_code == 200
    assert result.json()["data"]["status"] == "completed"
    return result.json()["data"]["quiz"]


def test_user_profile_and_history_require_a_valid_token(client):
    assert client.get("/api/v1/user/profile").status_code == 401
    assert (
        client.get(
            "/api/v1/user/profile",
            headers={"Authorization": "Bearer invalid"},
        ).status_code
        == 401
    )


def test_login_creates_user_and_profile_can_be_updated(client):
    token, user = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    assert user["nickname"] == "学习者"
    assert user["total_xp"] == 0
    profile = client.get("/api/v1/user/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["data"]["quiz_count"] == 0

    updated = client.put(
        "/api/v1/user/profile",
        headers=headers,
        json={"nickname": "新昵称", "avatar_url": "https://example.com/a.png"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["nickname"] == "新昵称"
    assert updated.json()["data"]["avatar_url"] == "https://example.com/a.png"

    assert client.put(
        "/api/v1/user/profile",
        headers=headers,
        json={"nickname": "   "},
    ).status_code == 422


def test_repeat_login_reuses_the_same_wechat_user(client):
    code = uuid4().hex
    first = client.post("/api/v1/user/login", json={"code": code}).json()["data"]
    second = client.post("/api/v1/user/login", json={"code": code}).json()["data"]

    assert first["user"]["id"] == second["user"]["id"]


def test_quiz_and_report_persist_only_for_authenticated_users_and_xp_is_idempotent(
    client,
):
    token, user = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    generate_quiz(client, "匿名学习")
    quiz = generate_quiz(client, "登录后学习", headers)
    report_request = {
        "quiz_id": quiz["quiz_id"],
        "topic": quiz["user_input"],
        "questions": quiz["questions"],
        "answer_records": [
            {
                "question_id": question["id"],
                "selected_answers": ["A"],
                "is_correct": False,
                "duration_ms": 1000,
            }
            for question in quiz["questions"]
        ],
    }

    first = client.post(
        "/api/v1/report/generate",
        headers=headers,
        json=report_request,
    )
    second = client.post(
        "/api/v1/report/generate",
        headers=headers,
        json=report_request,
    )
    assert first.status_code == second.status_code == 200

    profile = client.get("/api/v1/user/profile", headers=headers).json()["data"]
    assert profile["total_xp"] == 86
    assert profile["quiz_count"] == 1
    assert profile["correct_count"] == 4
    assert profile["average_accuracy"] == 80

    history = client.get("/api/v1/user/quizzes", headers=headers).json()["data"]
    assert history["total"] == 1
    assert history["items"][0]["quiz_id"] == quiz["quiz_id"]

    detail = client.get(
        f"/api/v1/user/quizzes/{quiz['quiz_id']}",
        headers=headers,
    )
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert len(detail_data["questions"]) == 5
    for question in detail_data["questions"]:
        assert {"stem", "options", "answer", "explanation"} <= question.keys()
    for answer_record in detail_data["answer_records"]:
        assert {"selected_answers", "is_correct"} <= answer_record.keys()

    answer_by_question = {
        record["question_id"]: record
        for record in detail_data["answer_records"]
    }
    assert answer_by_question["q1"]["is_correct"] is True
    assert answer_by_question["q4"]["selected_answers"] == ["A"]
    assert answer_by_question["q4"]["is_correct"] is False
    assert detail_data["report"]["xp_reward"] == 86


def test_anonymous_report_remains_available(client):
    quiz = generate_quiz(client, "匿名报告")
    response = client.post(
        "/api/v1/report/generate",
        json={
            "quiz_id": quiz["quiz_id"],
            "topic": quiz["user_input"],
            "questions": quiz["questions"],
            "answer_records": [
                {
                    "question_id": question["id"],
                    "selected_answers": ["A", "B"] if question["type"] == "multiple" else ["A"],
                    "is_correct": False,
                    "duration_ms": 1000,
                }
                for question in quiz["questions"]
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["xp_reward"] == 86


def test_history_is_isolated_between_users(client):
    owner_token, _ = login(client)
    other_token, _ = login(client)
    quiz = generate_quiz(
        client,
        "仅属于本人",
        {"Authorization": f"Bearer {owner_token}"},
    )
    response = client.get(
        f"/api/v1/user/quizzes/{quiz['quiz_id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404


def test_authenticated_user_cannot_save_another_users_quiz_report(client):
    owner_token, _ = login(client)
    other_token, _ = login(client)
    quiz = generate_quiz(
        client,
        "所有权校验",
        {"Authorization": f"Bearer {owner_token}"},
    )

    response = client.post(
        "/api/v1/report/generate",
        headers={"Authorization": f"Bearer {other_token}"},
        json={
            "quiz_id": quiz["quiz_id"],
            "topic": quiz["user_input"],
            "questions": quiz["questions"],
            "answer_records": [
                {
                    "question_id": question["id"],
                    "selected_answers": ["A", "B"] if question["type"] == "multiple" else ["A"],
                    "is_correct": True,
                    "duration_ms": 1000,
                }
                for question in quiz["questions"]
            ],
        },
    )

    assert response.status_code == 404


def test_invalid_optional_token_does_not_silently_become_anonymous(client):
    response = client.post(
        "/api/v1/quiz/generate",
        headers={"Authorization": "Bearer invalid"},
        json={"user_input": "验证失效 token"},
    )
    assert response.status_code == 401
