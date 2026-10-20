from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.quiz import router as quiz_router
from app.api.v1.routes.report import router as report_router
from app.api.v1.routes.user import router as user_router

__all__ = ["health_router", "quiz_router", "report_router", "user_router"]
