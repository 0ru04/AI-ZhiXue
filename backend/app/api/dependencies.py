from fastapi import Request

from app.core.config import get_settings
from app.core.config import Settings
from app.services.quiz_service import QuizService
from app.services.report_service import ReportService
from app.services.source_import_service import SourceImportService


def get_request_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_quiz_service() -> QuizService:
    return QuizService(get_settings())


def get_report_service() -> ReportService:
    return ReportService(get_settings())


def get_source_import_service() -> SourceImportService:
    return SourceImportService()
