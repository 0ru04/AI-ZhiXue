from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BLOCKED_TERMS = ("自杀教程", "炸弹制作", "制毒方法", "色情资源")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    deepseek_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DEEPSEEK_API_KEY", "deepseek_api_key"),
    )
    deepseek_model: str = Field(
        default="deepseek-flash",
        validation_alias=AliasChoices("DEEPSEEK_MODEL", "deepseek_model"),
    )
    deepseek_base_url: str = "https://api.deepseek.com"
    content_blocklist: str = Field(
        default="",
        validation_alias=AliasChoices("CONTENT_BLOCKLIST", "content_blocklist"),
    )
    cors_origins: str = Field(
        default="http://localhost:10086,http://127.0.0.1:10086",
        validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"),
    )
    llm_max_attempts: int = Field(default=2, ge=1, le=3)
    llm_timeout_seconds: float = Field(default=30, gt=0, le=120)
    database_url: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    test_database_url: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("TEST_DATABASE_URL", "test_database_url"),
    )
    wechat_app_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "WECHAT_APP_ID",
            "WECHAT_APPID",
            "wechat_app_id",
        ),
    )
    wechat_app_secret: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "WECHAT_APP_SECRET",
            "WECHAT_SECRET",
            "wechat_app_secret",
        ),
    )
    jwt_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("JWT_SECRET_KEY", "jwt_secret_key"),
    )
    jwt_expiration_days: int = Field(
        default=7,
        ge=1,
        le=90,
        validation_alias=AliasChoices(
            "JWT_EXPIRATION_DAYS",
            "jwt_expiration_days",
        ),
    )
    wechat_api_timeout_seconds: float = Field(
        default=5,
        gt=0,
        le=30,
        validation_alias=AliasChoices(
            "WECHAT_API_TIMEOUT_SECONDS",
            "wechat_api_timeout_seconds",
        ),
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def blocked_terms(self) -> tuple[str, ...]:
        configured = tuple(
            term.strip()
            for term in self.content_blocklist.split(",")
            if term.strip()
        )
        return DEFAULT_BLOCKED_TERMS + configured


@lru_cache
def get_settings() -> Settings:
    return Settings()
