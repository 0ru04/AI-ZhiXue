from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_request_settings
from app.core.config import Settings
from app.core.exceptions import UserResourceNotFoundError
from app.db.models import User
from app.db.session import get_required_db_session
from app.models.user import (
    LoginRequest,
    UserProfile,
    UserProfileUpdate,
)
from app.services.user_service import UserService
from app.services.wechat_provider import WechatLoginProvider


router = APIRouter(prefix="/user", tags=["user"])


def get_wechat_login_provider(
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> WechatLoginProvider:
    return WechatLoginProvider(settings)


def get_user_service(
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> UserService:
    return UserService(settings)


@router.post("/login")
async def login(
    request: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_required_db_session)],
    provider: Annotated[
        WechatLoginProvider,
        Depends(get_wechat_login_provider),
    ],
    service: Annotated[UserService, Depends(get_user_service)],
):
    service.ensure_login_configured()
    openid = await provider.exchange_code(request.code)
    result = await service.login(session, openid)
    return {
        "code": 0,
        "message": "ok",
        "data": result.model_dump(mode="json"),
    }


@router.get("/profile")
async def get_profile(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_required_db_session)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    profile: UserProfile = await service.get_profile(session, user)
    return {
        "code": 0,
        "message": "ok",
        "data": profile.model_dump(mode="json"),
    }


@router.put("/profile")
async def update_profile(
    request: UserProfileUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_required_db_session)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    result = await service.update_profile(session, user, request)
    return {
        "code": 0,
        "message": "ok",
        "data": result.model_dump(mode="json"),
    }


@router.get("/quizzes")
async def list_quizzes(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_required_db_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
):
    result = await service.list_quizzes(session, user, page, page_size)
    return {
        "code": 0,
        "message": "ok",
        "data": result.model_dump(mode="json"),
    }


@router.get("/quizzes/{quiz_id}")
async def get_quiz_detail(
    quiz_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_required_db_session)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    detail = await service.get_quiz_detail(session, user, quiz_id)
    if detail is None:
        raise UserResourceNotFoundError()
    return {
        "code": 0,
        "message": "ok",
        "data": detail.model_dump(mode="json"),
    }
