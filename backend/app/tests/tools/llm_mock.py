"""Mock LLMProvider —— 极简的 LLM 调用 mock，完全不依赖 OpenAI SDK 内部类型。

使用方式::

    mock = MockLLMProvider()
    mock.register_stream("hello", [StreamChunk(content="h"), StreamChunk(content="i")])
    mock.register_completion("hello", Completion(content="hi"))

    llm_client = LLMClient(config_manager, provider=mock)
"""

from collections.abc import Generator, Iterable
from typing import Any

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolUnionParam

from app.tools.llm import Completion, LLMProvider, StreamChunk


class MockLLMProvider(LLMProvider):
    """LLMProvider 的 mock 实现，不发起任何网络请求。

    按最后一条 user 消息的内容匹配预注册的响应。
    """

    def __init__(self, model_name: str = "mock-model") -> None:
        self.model_name = model_name
        self._stream_registry: dict[str, list[StreamChunk]] = {}
        self._completion_registry: dict[str, Completion] = {}
        self._tool_stream_registry: dict[str, list[StreamChunk]] = {}
        self.call_log: list[dict[str, Any]] = []

    # ---- 注册 API ----

    def register_stream(self, prompt: str, chunks: list[StreamChunk]) -> None:
        """按 prompt 精确匹配注册流式响应"""
        self._stream_registry[prompt] = chunks

    def register_completion(self, prompt: str, response: Completion) -> None:
        """按 prompt 精确匹配注册非流式响应"""
        self._completion_registry[prompt] = response

    def register_tool_stream(self, prompt: str, chunks: list[StreamChunk]) -> None:
        """按 prompt 精确匹配注册带工具调用的流式响应"""
        self._tool_stream_registry[prompt] = chunks

    # ---- LLMProvider 接口实现 ----

    def create_completion(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        *,
        tools: Iterable[ChatCompletionToolUnionParam] | None = None,
        extra_body: dict | None = None,
    ) -> Completion:
        self.call_log.append({"model": model, "stream": False, "tools": bool(tools)})

        resp = self._find_response(self._completion_registry, messages)
        if resp is None:
            resp = Completion(content="mock default response")
        return resp

    def create_stream(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        *,
        tools: Iterable[ChatCompletionToolUnionParam] | None = None,
        extra_body: dict | None = None,
    ) -> Generator[StreamChunk, Any]:
        self.call_log.append({"model": model, "stream": True, "tools": bool(tools)})

        # 有工具时优先匹配 tool_stream 注册表，fallback 到普通 stream
        if tools:
            chunks = self._find_response(self._tool_stream_registry, messages)
            if chunks is None:
                chunks = self._find_response(self._stream_registry, messages)
            if chunks is None:
                chunks = [StreamChunk(content="mock default tool response", finish_reason="stop")]
        else:
            chunks = self._find_response(self._stream_registry, messages)
            if chunks is None:
                chunks = [StreamChunk(content="mock default stream response", finish_reason="stop")]

        yield from chunks

    # ---- 匹配逻辑 ----

    @staticmethod
    def _find_response(registry: dict[str, Any], messages: list[ChatCompletionMessageParam]) -> Any:
        """从 registry 中按最后一条 user 消息匹配注册项（先精确匹配，再子串匹配）"""
        user_content = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                raw = m.get("content", "")
                user_content = raw if isinstance(raw, str) else str(raw)
                break

        if user_content in registry:
            return registry[user_content]

        # 子串匹配
        for key, value in registry.items():
            if key in user_content:
                return value

        return None
