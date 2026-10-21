from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from app.models.quiz import QuizGenerationOutput


class ToolCallingFakeModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def test_agent_executes_model_selected_tool():
    tool_calls = []

    def search(topic: str) -> str:
        tool_calls.append(topic)
        return "Reference material"

    model = ToolCallingFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search",
                        "args": {"topic": "plants"},
                        "id": "search-call",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="A concise knowledge summary."),
        ]
    )
    search_tool = StructuredTool.from_function(
        func=search,
        name="search",
        description="Search reference material for a topic.",
    )
    agent = create_agent(model=model, tools=[search_tool])

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Learn about plants."}]}
    )

    assert tool_calls == ["plants"]
    assert result["messages"][-1].content == "A concise knowledge summary."


def test_deepseek_model_configuration_supports_agent_and_structured_output():
    model = ChatOpenAI(
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        api_key="test-key",
        temperature=0,
        max_retries=0,
    )
    search_tool = StructuredTool.from_function(
        func=lambda topic: topic,
        name="search",
        description="Search reference material for a topic.",
    )

    agent_model = model.bind_tools([search_tool])
    structured_model = model.with_structured_output(
        QuizGenerationOutput,
        method="function_calling",
    )

    assert agent_model is not None
    assert structured_model is not None
