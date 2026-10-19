from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_report_service
from app.models.report import ReportRequest
from app.services.report_service import ReportService


router = APIRouter()


@router.post("/report/generate")
async def generate_report(
    request: ReportRequest,
    service: Annotated[ReportService, Depends(get_report_service)],
):
    report = await service.generate(request)
    return {"code": 0, "message": "ok", "data": report.model_dump()}
