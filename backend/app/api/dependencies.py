from app.core.config import get_settings
from app.services.quiz_service import QuizService
from app.services.report_service import ReportService


def get_quiz_service() -> QuizService:
    return QuizService(get_settings())


def get_report_service() -> ReportService:
    return ReportService(get_settings())
