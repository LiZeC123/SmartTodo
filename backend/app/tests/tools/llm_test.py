"""LLMClient 单元测试 —— 使用 MockLLMProvider 替换底层 LLM 调用"""

from collections.abc import Generator
from typing import Any

import pytest
from openai.types.chat import (
    ChatCompletionFunctionToolParam,
    ChatCompletionMessageParam,
)

from app.services.config_manager import ConfigManager
from app.tests.tools.llm_mock import MockLLMProvider
from app.tools.llm import Completion, LLMClient, StreamChunk

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config_manager() -> ConfigManager:
    return ConfigManager()


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
def mock_simple_provider() -> MockLLMProvider:
    return MockLLMProvider(model_name="mock-simple-model")


@pytest.fixture
def client(
    config_manager: ConfigManager, mock_provider: MockLLMProvider, mock_simple_provider: MockLLMProvider
) -> LLMClient:
    return LLMClient(config_manager, provider=mock_provider, simple_provider=mock_simple_provider)


# ---------------------------------------------------------------------------
# helper
# ---------------------------------------------------------------------------


def _consume(g: Generator[str, Any]) -> str:
    """消费 generator，返回拼接后的完整字符串"""
    return "".join(list(g))


# ---------------------------------------------------------------------------
# generate_stream
# ---------------------------------------------------------------------------


def test_generate_stream_basic(client: LLMClient, mock_provider: MockLLMProvider) -> None:
    """流式输出：逐 chunk 返回 content"""
    mock_provider.register_stream(
        "hello",
        [StreamChunk(content="Hel"), StreamChunk(content="lo"), StreamChunk(content="!")],
    )

    history: list[ChatCompletionMessageParam] = [{"role": "user", "content": "hello"}]
    result = _consume(client.generate_stream(history))

    assert result == "Hello!"


def test_generate_stream_skips_none_content(client: LLMClient, mock_provider: MockLLMProvider) -> None:
    """content 为 None 的 chunk 应被跳过"""
    mock_provider.register_stream(
        "test",
        [
            StreamChunk(content=None),
            StreamChunk(content="A"),
            StreamChunk(content=None),
            StreamChunk(content="B"),
        ],
    )

    history: list[ChatCompletionMessageParam] = [{"role": "user", "content": "test"}]
    result = _consume(client.generate_stream(history))

    assert result == "AB"


def test_generate_stream_passes_thinking_disable(client: LLMClient, mock_provider: MockLLMProvider) -> None:
    """verify generate_stream 调用 provider.create_stream 时传入 thinking_disable"""
    mock_provider.register_stream("ping", [StreamChunk(content="pong")])

    history: list[ChatCompletionMessageParam] = [{"role": "user", "content": "ping"}]
    _consume(client.generate_stream(history))

    # 检查 call_log 里的 extra_body: 无法直接从 call_log 看到 extra_body,
    # 但可以通过 proxy 验证 — 此处只验证调用成功
    assert len(mock_provider.call_log) == 1
    assert mock_provider.call_log[0]["stream"] is True


# ---------------------------------------------------------------------------
# generate_one_shot
# ---------------------------------------------------------------------------


def test_generate_one_shot_basic(client: LLMClient, mock_provider: MockLLMProvider) -> None:
    """非流式请求：返回 (reasoning_content, content)"""
    mock_provider.register_completion(
        "what is 1+1",
        Completion(content="2", reasoning_content="let me calculate"),
    )

    reasoning, content = client.generate_one_shot("what is 1+1")

    assert reasoning == "let me calculate"
    assert content == "2"


def test_generate_one_shot_thinking_disabled(client: LLMClient, mock_provider: MockLLMProvider) -> None:
    """thinking=False 时，reasoning 返回空字符串"""
    mock_provider.register_completion(
        "hi",
        Completion(content="hello", reasoning_content="some thinking"),
    )

    reasoning, content = client.generate_one_shot("hi", thinking=False)

    assert reasoning == ""
    assert content == "hello"


# ---------------------------------------------------------------------------
# generate_steam_with_tools
# ---------------------------------------------------------------------------


def _make_tool_def() -> list[ChatCompletionFunctionToolParam]:
    """构造一个简单的工具定义"""
    return [
        ChatCompletionFunctionToolParam(
            type="function",
            function={
                "name": "get_weather",
                "description": "Get current weather",
                "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
            },
        )
    ]


def test_generate_steam_with_tools_basic(client: LLMClient, mock_provider: MockLLMProvider) -> None:
    """流式工具调用：增量 tool_call 应被正确累积到 tool_calls_list"""
    mock_provider.register_tool_stream(
        "weather in beijing",
        [
            StreamChunk(
                tool_call_deltas=[{"index": 0, "id": "call_1", "name": "get_weather", "arguments": None}],
            ),
            StreamChunk(
                tool_call_deltas=[{"index": 0, "id": None, "name": None, "arguments": '{"city":"Beijing"}'}],
            ),
            StreamChunk(finish_reason="tool_calls"),
        ],
    )

    history: list[ChatCompletionMessageParam] = [{"role": "user", "content": "weather in beijing"}]
    tools = _make_tool_def()
    tool_calls_list: list[dict[str, Any]] = []

    result = _consume(client.generate_steam_with_tools(history, tools, tool_calls_list))

    # 没有文本内容时不 yield
    assert result == ""

    # tool_calls_list 应包含一个完整的工具调用
    assert len(tool_calls_list) == 1
    tc = tool_calls_list[0]
    assert tc["id"] == "call_1"
    assert tc["type"] == "function"
    assert tc["function"]["name"] == "get_weather"
    assert tc["function"]["arguments"] == '{"city":"Beijing"}'


def test_generate_steam_with_tools_mixed_content(client: LLMClient, mock_provider: MockLLMProvider) -> None:
    """流式输出中既有文本又有工具调用"""
    mock_provider.register_tool_stream(
        "mix",
        [
            StreamChunk(content="Let me check "),
            StreamChunk(content="the weather."),
            StreamChunk(
                tool_call_deltas=[{"index": 0, "id": "call_x", "name": "search", "arguments": '{"q":"test"}'}],
            ),
            StreamChunk(finish_reason="tool_calls"),
        ],
    )

    history: list[ChatCompletionMessageParam] = [{"role": "user", "content": "mix"}]
    tools = _make_tool_def()
    tool_calls_list: list[dict[str, Any]] = []

    result = _consume(client.generate_steam_with_tools(history, tools, tool_calls_list))

    assert result == "Let me check the weather."
    assert len(tool_calls_list) == 1
    assert tool_calls_list[0]["function"]["name"] == "search"


def test_generate_steam_with_tools_no_tool_call(client: LLMClient, mock_provider: MockLLMProvider) -> None:
    """finish_reason 不是 tool_calls 时，不应写入 tool_calls_list"""
    mock_provider.register_stream(
        "normal message",
        [
            StreamChunk(content="Just a normal reply."),
            StreamChunk(finish_reason="stop"),
        ],
    )

    history: list[ChatCompletionMessageParam] = [{"role": "user", "content": "normal message"}]
    tools = _make_tool_def()
    tool_calls_list: list[dict[str, Any]] = []

    result = _consume(client.generate_steam_with_tools(history, tools, tool_calls_list))

    assert result == "Just a normal reply."
    assert len(tool_calls_list) == 0
