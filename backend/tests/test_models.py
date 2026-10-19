import pytest
from pydantic import ValidationError

from app.models.quiz import Quiz, Question
from app.models.report import ReportRequest


def test_quiz_requires_three_single_one_multiple_and_one_judge(question_data):
    assert len(Quiz(
        quiz_id="quiz_test",
        title="Test",
        summary="Summary",
        source_type="text",
        user_input="Topic",
        questions=question_data,
    ).questions) == 5

    question_data[0]["type"] = "multiple"
    with pytest.raises(ValidationError):
        Quiz(
            quiz_id="quiz_test",
            title="Test",
            summary="Summary",
            source_type="text",
            user_input="Topic",
            questions=question_data,
        )


def test_question_rejects_answers_not_in_options(question_data):
    question_data[0]["answer"] = ["Z"]

    with pytest.raises(ValidationError):
        Question.model_validate(question_data[0])


def test_report_rejects_duplicate_or_missing_answer_records(question_data):
    records = [
        {
            "question_id": f"q{index}",
            "selected_answers": ["A"],
            "duration_ms": 100,
        }
        for index in range(1, 6)
    ]
    records[-1]["question_id"] = "q4"

    with pytest.raises(ValidationError):
        ReportRequest(
            quiz_id="quiz_test",
            topic="Test",
            questions=question_data,
            answer_records=records,
        )


def test_report_rejects_selected_option_not_in_question(question_data):
    records = [
        {
            "question_id": f"q{index}",
            "selected_answers": ["A"],
            "duration_ms": 100,
        }
        for index in range(1, 6)
    ]
    records[0]["selected_answers"] = ["Z"]

    with pytest.raises(ValidationError):
        ReportRequest(
            quiz_id="quiz_test",
            topic="Test",
            questions=question_data,
            answer_records=records,
        )
