from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.exceptions import LLMConfigurationError


def create_chat_model(settings: Settings, temperature: float):
    if (
        settings.deepseek_api_key is None
        or not settings.deepseek_api_key.get_secret_value().strip()
    ):
        raise LLMConfigurationError()

    return ChatOpenAI(
        model=settings.deepseek_model,
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key.get_secret_value(),
        temperature=temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=0,
        extra_body={"thinking": {"type": "disabled"}},
    )


def create_structured_chain(
    schema: type[BaseModel],
    prompt: ChatPromptTemplate,
    temperature: float,
):
    model = create_chat_model(get_settings(), temperature)
    return prompt | model.with_structured_output(schema, method="function_calling")
