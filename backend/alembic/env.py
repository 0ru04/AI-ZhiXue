import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.models import Base
from app.db.session import async_database_url


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> URL:
    settings = get_settings()
    target = context.get_x_argument(as_dictionary=True).get("database", "test")
    if target == "test":
        configured_url = settings.test_database_url
    elif target == "production":
        configured_url = settings.database_url
    else:
        raise ValueError("Migration target must be 'test' or 'production'")
    if configured_url is None:
        raise ValueError(f"{target.upper()}_DATABASE_URL is not configured")

    selected = make_url(configured_url.get_secret_value())
    if target == "test" and settings.database_url is not None:
        production = make_url(settings.database_url.get_secret_value())
        if (
            selected.host,
            selected.port or 3306,
            selected.database,
        ) == (
            production.host,
            production.port or 3306,
            production.database,
        ):
            raise ValueError("Test and production database targets must differ")
    return async_database_url(configured_url.get_secret_value())


def run_migrations_offline() -> None:
    url = database_url()
    context.configure(
        url=url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    config.set_main_option(
        "sqlalchemy.url",
        database_url().render_as_string(hide_password=False).replace("%", "%%"),
    )
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
