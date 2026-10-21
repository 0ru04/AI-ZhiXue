import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_knowledge_agent_settings_defaults_allow_missing_tavily_key():
    settings = Settings(_env_file=None)

    assert settings.tavily_api_key is None
    assert settings.knowledge_agent_enabled is True
    assert settings.tavily_default_max_results == 5
    assert settings.knowledge_agent_max_tool_calls == 4
    assert settings.tavily_tool_timeout_seconds == 10
    assert settings.knowledge_agent_timeout_seconds == 20


def test_knowledge_agent_settings_accept_secret_and_disabled_mode():
    settings = Settings(
        _env_file=None,
        tavily_api_key="test-key",
        knowledge_agent_enabled=False,
        tavily_default_max_results=8,
    )

    assert isinstance(settings.tavily_api_key, SecretStr)
    assert settings.tavily_api_key.get_secret_value() == "test-key"
    assert settings.knowledge_agent_enabled is False
    assert settings.tavily_default_max_results == 8


def test_knowledge_agent_settings_read_environment_names(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("KNOWLEDGE_AGENT_ENABLED", "false")
    monkeypatch.setenv("TAVILY_DEFAULT_MAX_RESULTS", "6")

    settings = Settings(_env_file=None)

    assert settings.tavily_api_key.get_secret_value() == "test-key"
    assert settings.knowledge_agent_enabled is False
    assert settings.tavily_default_max_results == 6


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("tavily_default_max_results", 0),
        ("tavily_default_max_results", 11),
        ("knowledge_agent_max_tool_calls", 0),
        ("knowledge_agent_max_tool_calls", 11),
        ("tavily_tool_timeout_seconds", 0),
        ("tavily_tool_timeout_seconds", 31),
        ("knowledge_agent_timeout_seconds", 0),
        ("knowledge_agent_timeout_seconds", 61),
    ],
)
def test_knowledge_agent_settings_reject_values_outside_bounds(setting, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{setting: value})
