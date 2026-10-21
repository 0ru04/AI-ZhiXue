from fastapi import Request

from app.core.config import Settings, get_settings
from app.services.live_knowledge_service import LiveKnowledgeService
from app.services.quiz_service import QuizService
from app.services.report_service import ReportService
from app.services.source_import_service import SourceImportService


def get_request_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_quiz_service(request: Request) -> QuizService:
    settings = request.app.state.settings
    return QuizService(settings, knowledge_service=LiveKnowledgeService(settings))


def get_report_service() -> ReportService:
    return ReportService(get_settings())


def get_source_import_service() -> SourceImportService:
    return SourceImportService()
