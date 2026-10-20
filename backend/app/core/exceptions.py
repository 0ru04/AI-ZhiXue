class APIError(Exception):
    def __init__(self, message: str, *, code: int, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ContentBlockedError(APIError):
    def __init__(self) -> None:
        super().__init__(
            "内容暂不支持生成，请调整后重试",
            code=4003,
            status_code=400,
        )


class LLMConfigurationError(APIError):
    def __init__(self) -> None:
        super().__init__(
            "AI 服务尚未配置，请检查后端密钥设置",
            code=5031,
            status_code=503,
        )


class AIProviderError(APIError):
    def __init__(self) -> None:
        super().__init__(
            "AI 生成暂时失败，请稍后重试",
            code=5001,
            status_code=502,
        )


class AuthenticationError(APIError):
    def __init__(self) -> None:
        super().__init__(
            "登录状态无效，请重新登录",
            code=4010,
            status_code=401,
        )


class UserSystemConfigurationError(APIError):
    def __init__(self, message: str = "用户系统尚未配置，请联系管理员") -> None:
        super().__init__(
            message,
            code=5032,
            status_code=503,
        )


class WechatLoginError(APIError):
    def __init__(self) -> None:
        super().__init__(
            "微信登录暂时不可用，请稍后重试",
            code=5021,
            status_code=502,
        )


class UserResourceNotFoundError(APIError):
    def __init__(self) -> None:
        super().__init__(
            "记录不存在",
            code=4040,
            status_code=404,
        )
