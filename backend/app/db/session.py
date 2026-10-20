import logging
from collections.abc import AsyncIterator
from typing import cast

from fastapi import Depends, Request
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.exceptions import UserSystemConfigurationError


logger = logging.getLogger(__name__)


def async_database_url(value: str) -> URL:
    url = make_url(value)
    if url.drivername == "mysql+pymysql":
        logger.warning(
            "DATABASE_URL uses mysql+pymysql; switching its SQLAlchemy driver to asyncmy"
        )
        return url.set(drivername="mysql+asyncmy")
    if url.drivername != "mysql+asyncmy":
        raise ValueError("DATABASE_URL must use the mysql+asyncmy driver")
    return url


def create_database(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        async_database_url(database_url),
        pool_pre_ping=True,
    )
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def get_optional_db_session(
    request: Request,
) -> AsyncIterator[AsyncSession | None]:
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if session_factory is None:
        yield None
        return
    async with cast(async_sessionmaker[AsyncSession], session_factory)() as session:
        yield session


async def get_required_db_session(
    session: AsyncSession | None = Depends(get_optional_db_session),
) -> AsyncIterator[AsyncSession]:
    if session is None:
        raise UserSystemConfigurationError("用户数据库尚未配置")
    yield session
