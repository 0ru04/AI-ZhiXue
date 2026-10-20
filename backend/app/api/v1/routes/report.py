from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_dependencies import get_optional_current_user
from app.api.dependencies import get_report_service
from app.core.exceptions import UserSystemConfigurationError
from app.db.models import User
from app.db.session import get_optional_db_session
from app.models.report import ReportRequest
from app.services.persistence_service import PersistenceService
from app.services.report_service import ReportService


router = APIRouter()


@router.post("/report/generate")
async def generate_report(
    request: ReportRequest,
    service: Annotated[ReportService, Depends(get_report_service)],
    user: Annotated[User | None, Depends(get_optional_current_user)],
    session: Annotated[AsyncSession | None, Depends(get_optional_db_session)],
):
    report = await service.generate(request)
    if user is not None:
        if session is None:
            raise UserSystemConfigurationError("用户数据库尚未配置")
        await PersistenceService().save_report(session, user, request, report)
    return {"code": 0, "message": "ok", "data": report.model_dump()}
