from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_request_settings
from app.core.config import Settings
from app.core.exceptions import AuthenticationError, UserSystemConfigurationError
from app.db.models import User
from app.db.session import get_optional_db_session


bearer_scheme = HTTPBearer(auto_error=False)


def _get_user_id(token: str, settings: Settings) -> int:
    if (
        settings.jwt_secret_key is None
        or len(settings.jwt_secret_key.get_secret_value()) < 32
    ):
        raise UserSystemConfigurationError("JWT_SECRET_KEY 未配置")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise AuthenticationError() from error


async def get_optional_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: Annotated[
        AsyncSession | None,
        Depends(get_optional_db_session),
    ],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> User | None:
    if credentials is None:
        authorization = request.headers.get("authorization")
        if authorization:
            raise AuthenticationError()
        return None
    user_id = _get_user_id(credentials.credentials, settings)
    if session is None:
        raise UserSystemConfigurationError("用户数据库尚未配置")
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise AuthenticationError()
    return user


async def get_current_user(
    user: Annotated[User | None, Depends(get_optional_current_user)],
) -> User:
    if user is None:
        raise AuthenticationError()
    return user
