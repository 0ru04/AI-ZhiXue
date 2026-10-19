import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.routes import health_router, quiz_router, report_router
from app.core.config import get_settings
from app.core.exceptions import APIError


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(
        title="AI智学 API",
        description="把学习材料转成闯关题目和个性化复盘报告",
        version="1.0.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(quiz_router, prefix="/api/v1")
    application.include_router(report_router, prefix="/api/v1")

    @application.exception_handler(APIError)
    async def handle_api_error(_request: Request, error: APIError):
        return JSONResponse(
            status_code=error.status_code,
            content={
                "code": error.code,
                "message": error.message,
                "data": None,
            },
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        _error: RequestValidationError,
    ):
        return JSONResponse(
            status_code=422,
            content={
                "code": 4220,
                "message": "请求参数有误",
                "data": None,
            },
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, error: Exception):
        logger.error(
            "Unhandled API error",
            exc_info=(type(error), error, error.__traceback__),
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": 5000,
                "message": "服务器暂时无法处理，请稍后重试",
                "data": None,
            },
        )

    return application


app = create_app()
