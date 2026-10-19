import pytest

from app.models.quiz import Quiz
from app.models.report import AnswerRecord, ReportRequest


@pytest.fixture
def question_data():
    return [
        {
            "id": "q1",
            "type": "single",
            "stem": "Which option is correct?",
            "options": [{"key": "A", "text": "Correct"}, {"key": "B", "text": "Wrong"}],
            "answer": ["A"],
            "explanation": "A is correct.",
            "knowledge_point": "Basics",
            "difficulty": "easy",
        },
        {
            "id": "q2",
            "type": "single",
            "stem": "Which option is correct?",
            "options": [{"key": "A", "text": "Correct"}, {"key": "B", "text": "Wrong"}],
            "answer": ["A"],
            "explanation": "A is correct.",
            "knowledge_point": "Basics",
            "difficulty": "easy",
        },
        {
            "id": "q3",
            "type": "single",
            "stem": "Which option is correct?",
            "options": [{"key": "A", "text": "Correct"}, {"key": "B", "text": "Wrong"}],
            "answer": ["A"],
            "explanation": "A is correct.",
            "knowledge_point": "Applications",
            "difficulty": "medium",
        },
        {
            "id": "q4",
            "type": "multiple",
            "stem": "Choose both correct options.",
            "options": [
                {"key": "A", "text": "Correct"},
                {"key": "B", "text": "Wrong"},
                {"key": "C", "text": "Correct"},
            ],
            "answer": ["A", "C"],
            "explanation": "A and C are correct.",
            "knowledge_point": "Applications",
            "difficulty": "medium",
        },
        {
            "id": "q5",
            "type": "judge",
            "stem": "This statement is true.",
            "options": [{"key": "A", "text": "True"}, {"key": "B", "text": "False"}],
            "answer": ["A"],
            "explanation": "The statement is true.",
            "knowledge_point": "Review",
            "difficulty": "easy",
        },
    ]


@pytest.fixture
def quiz(question_data):
    return Quiz(
        quiz_id="quiz_test",
        title="Test topic",
        summary="A quiz for tests.",
        source_type="text",
        user_input="Test topic",
        questions=question_data,
    )


@pytest.fixture
def report_request(question_data):
    selected = [["A"], ["A"], ["B"], ["A"], ["A"]]
    return ReportRequest(
        quiz_id="quiz_test",
        topic="Test topic",
        questions=question_data,
        answer_records=[
            AnswerRecord(
                question_id=f"q{index}",
                selected_answers=answers,
                is_correct=False,
                duration_ms=1000,
            )
            for index, answers in enumerate(selected, start=1)
        ],
    )
