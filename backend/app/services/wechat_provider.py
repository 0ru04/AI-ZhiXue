import httpx

from app.core.config import Settings
from app.core.exceptions import UserSystemConfigurationError, WechatLoginError


WECHAT_CODE2SESSION_URL = (
    "https://api.weixin.qq.com/sns/jscode2session"
)


class WechatLoginProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def exchange_code(self, code: str) -> str:
        if (
            not self.settings.wechat_app_id
            or self.settings.wechat_app_secret is None
            or not self.settings.wechat_app_secret.get_secret_value()
        ):
            raise UserSystemConfigurationError(
                "WECHAT_APP_ID 和 WECHAT_APP_SECRET 未配置"
            )

        params = {
            "appid": self.settings.wechat_app_id,
            "secret": self.settings.wechat_app_secret.get_secret_value(),
            "js_code": code,
            "grant_type": "authorization_code",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.wechat_api_timeout_seconds
            ) as client:
                response = await client.get(WECHAT_CODE2SESSION_URL, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise WechatLoginError() from error

        if not isinstance(payload, dict) or payload.get("errcode"):
            raise WechatLoginError()
        openid = payload.get("openid")
        if not isinstance(openid, str) or not openid:
            raise WechatLoginError()
        return openid
