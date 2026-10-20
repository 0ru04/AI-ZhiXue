import asyncio

import pytest

from app.core.config import Settings
from app.core.exceptions import UserSystemConfigurationError, WechatLoginError
from app.services.wechat_provider import WechatLoginProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    payload = {"openid": "test-openid"}
    request_args = None

    def __init__(self, *, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, url, *, params):
        type(self).request_args = (url, params)
        return FakeResponse(type(self).payload)


def test_wechat_provider_exchanges_code_without_network(monkeypatch):
    FakeAsyncClient.payload = {"openid": "wx-user-1"}
    monkeypatch.setattr(
        "app.services.wechat_provider.httpx.AsyncClient",
        FakeAsyncClient,
    )
    settings = Settings(
        wechat_app_id="app-id",
        wechat_app_secret="app-secret",
    )

    openid = asyncio.run(WechatLoginProvider(settings).exchange_code("wx-code"))

    assert openid == "wx-user-1"
    url, params = FakeAsyncClient.request_args
    assert url.endswith("/sns/jscode2session")
    assert params["js_code"] == "wx-code"
    assert params["appid"] == "app-id"
    assert params["secret"] == "app-secret"


@pytest.mark.parametrize(
    "payload",
    [
        {"errcode": 40029, "errmsg": "invalid code"},
        {"session_key": "missing openid"},
    ],
)
def test_wechat_provider_rejects_invalid_provider_responses(monkeypatch, payload):
    FakeAsyncClient.payload = payload
    monkeypatch.setattr(
        "app.services.wechat_provider.httpx.AsyncClient",
        FakeAsyncClient,
    )
    settings = Settings(
        wechat_app_id="app-id",
        wechat_app_secret="app-secret",
    )

    with pytest.raises(WechatLoginError):
        asyncio.run(WechatLoginProvider(settings).exchange_code("invalid-code"))


def test_wechat_provider_requires_app_credentials():
    settings = Settings(_env_file=None, wechat_app_id="app-id")
    provider = WechatLoginProvider(settings)

    with pytest.raises(UserSystemConfigurationError):
        asyncio.run(provider.exchange_code("wx-code"))
