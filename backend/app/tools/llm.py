from collections.abc import Generator, Iterable
from dataclasses import dataclass
from typing import Any

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolUnionParam,
)

from app.services.config_manager import ConfigManager
from app.template.prompt import AnyQuerySystemPrompt
from app.tools.log import logger

thinking_enable = {"thinking": {"type": "enabled"}}
thinking_disable = {"thinking": {"type": "disabled"}}


# ---------------------------------------------------------------------------
# 简单数据类型 —— 解耦 OpenAI SDK 内部类型，方便测试 mock
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class StreamChunk:
    """流式响应的单个 chunk，与 OpenAI SDK 类型解耦"""

    content: str | None = None
    reasoning_content: str | None = None
    finish_reason: str | None = None
    # tool_call_deltas: [{index, id, name, arguments}, ...]，flatten 了 function 嵌套
    tool_call_deltas: list[dict[str, Any]] | None = None


@dataclass(slots=True)
class Completion:
    """非流式响应，与 OpenAI SDK 类型解耦"""

    content: str = ""
    reasoning_content: str = ""


# ---------------------------------------------------------------------------
# LLMProvider — 封装底层 LLM SDK 调用
# ---------------------------------------------------------------------------


class LLMProvider:
    """LLM API 调用接口，封装底层 SDK（OpenAI 等）的调用细节。

    子类只需实现 create_completion 和 create_stream 两个方法，
    返回简单的 StreamChunk / Completion 数据类型。
    """

    def create_completion(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        *,
        tools: Iterable[ChatCompletionToolUnionParam] | None = None,
        extra_body: dict | None = None,
    ) -> Completion:
        raise NotImplementedError

    def create_stream(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        *,
        tools: Iterable[ChatCompletionToolUnionParam] | None = None,
        extra_body: dict | None = None,
    ) -> Generator[StreamChunk, Any]:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """基于 OpenAI SDK 的 LLMProvider 实现"""

    def __init__(self, api_key: str, base_url: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def create_completion(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        *,
        tools: Iterable[ChatCompletionToolUnionParam] | None = None,
        extra_body: dict | None = None,
    ) -> Completion:
        kwargs: dict[str, Any] = {"model": model, "messages": messages, "extra_body": extra_body}
        if tools:
            kwargs["tools"] = tools

        response = self._client.chat.completions.create(**kwargs)

        msg = response.choices[0].message
        return Completion(
            content=msg.content or "",
            reasoning_content=getattr(msg, "reasoning_content", "") or "",
        )

    def create_stream(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        *,
        tools: Iterable[ChatCompletionToolUnionParam] | None = None,
        extra_body: dict | None = None,
    ) -> Generator[StreamChunk, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "extra_body": extra_body,
        }
        if tools:
            kwargs["tools"] = tools

        response = self._client.chat.completions.create(**kwargs)

        for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            finish_reason: str | None = chunk.choices[0].finish_reason

            # 提取 reasoning_content（OpenAI SDK 扩展属性）
            reasoning: str | None = getattr(delta, "reasoning_content", None)

            # 提取 tool_call deltas，flatten function 嵌套
            tc_deltas: list[dict[str, Any]] | None = None
            if delta.tool_calls:
                tc_deltas = []
                for tc in delta.tool_calls:
                    tc_deltas.append(
                        {
                            "index": tc.index,
                            "id": tc.id,
                            "name": tc.function.name if tc.function else None,
                            "arguments": tc.function.arguments if tc.function else None,
                        }
                    )

            yield StreamChunk(
                content=delta.content,
                reasoning_content=reasoning,
                finish_reason=finish_reason,
                tool_call_deltas=tc_deltas,
            )


# ---------------------------------------------------------------------------
# LLMClient
# ---------------------------------------------------------------------------


class LLMClient:
    def __init__(
        self,
        config_manager: ConfigManager,
        provider: LLMProvider | None = None,
        simple_provider: LLMProvider | None = None,
    ) -> None:
        if provider is not None:
            self.provider = provider
            self.model_name = "mock-model"
        else:
            base_url, api_key, model_name = config_manager.get_llm_info()
            self.provider = OpenAIProvider(api_key=api_key, base_url=base_url)
            self.model_name = model_name

        if simple_provider is not None:
            self.simple_provider = simple_provider
            self.simple_model_name = "mock-simple-model"
        else:
            base_url, api_key, model_name = config_manager.get_tool_llm_info()
            self.simple_provider = OpenAIProvider(api_key=api_key, base_url=base_url)
            self.simple_model_name = model_name

        logger.info(f"主模型名: {self.model_name} 简单模型名: {self.simple_model_name}")

        self.history_space: dict[str, list[ChatCompletionMessageParam]] = {}

    def generate_stream(self, history: list[ChatCompletionMessageParam]) -> Generator[str, Any]:
        stream = self.provider.create_stream(self.model_name, history, extra_body=thinking_disable)

        for chunk in stream:
            if chunk.content is not None:
                yield chunk.content

    def generate_stream_with_prompt(self, prompt: str, *, thinking=True, simple_client=False):
        """单次流式请求模型, 返回思考内容和模型回复"""
        provider, model_name, extra_body = self._get_provider_and_body(thinking, simple_client)

        stream = provider.create_stream(
            model_name,
            [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt},
            ],
            extra_body=extra_body,
        )

        for chunk in stream:
            if chunk.reasoning_content is not None:
                yield chunk.reasoning_content
            if chunk.content is not None:
                yield chunk.content

    def generate_one_shot(self, prompt: str, *, thinking=True, simple_client=False):
        """单次非流式请求模型, 返回思考内容和模型回复"""
        provider, model_name, extra_body = self._get_provider_and_body(thinking, simple_client)

        result = provider.create_completion(
            model_name,
            [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt},
            ],
            extra_body=extra_body,
        )

        reasoning_content = result.reasoning_content if thinking else ""
        content = result.content
        return reasoning_content, content

    def generate_one_shot_with_history(
        self, prompt: str, history_tag: str, *, thinking=True, simple_client=False
    ) -> str:
        provider, model_name, extra_body = self._get_provider_and_body(thinking, simple_client)
        history_list = self.get_history(history_tag)
        history_list.append({"role": "user", "content": prompt})

        result = provider.create_completion(
            model_name,
            history_list,
            extra_body=extra_body,
        )

        content = result.content
        if content:
            history_list.append({"role": "assistant", "content": content})
            return content
        return "查询结果为空"

    def _get_provider_and_body(self, thinking: bool, simple_client: bool) -> tuple[LLMProvider, str, dict]:
        provider = self.simple_provider if simple_client else self.provider
        model_name = self.simple_model_name if simple_client else self.model_name
        extra_body = thinking_enable if thinking else thinking_disable
        return provider, model_name, extra_body

    def get_history(self, name: str) -> list[ChatCompletionMessageParam]:
        history = self.history_space.get(name)
        if history is None:
            init_history: list[ChatCompletionMessageParam] = [{"role": "system", "content": AnyQuerySystemPrompt}]
            self.history_space[name] = init_history
            return init_history

        return history

    @staticmethod
    def truncate_list_by_threshold(
        str_list: list[ChatCompletionMessageParam], threshold: int
    ) -> list[ChatCompletionMessageParam]:
        # 边界处理：空列表直接返回
        if not str_list:
            return []

        total_length = 0
        # 从后往前遍历列表，记录索引
        for idx in reversed(range(len(str_list))):
            # 累加当前字符串长度
            content: str = str_list[idx].get("content")  # type: ignore
            total_length += len(content)
            # 达到阈值，保留从当前索引到末尾的所有元素
            if total_length >= threshold:
                return str_list[idx:]

        # 所有元素累加都未达到阈值，返回全部
        return str_list

    def generate_steam_with_tools(
        self,
        history: list[ChatCompletionMessageParam],
        tools: Iterable[ChatCompletionToolUnionParam],
        tool_calls_list: list,
    ) -> Generator[str, Any]:
        stream = self.provider.create_stream(self.model_name, history, tools=tools, extra_body=thinking_disable)

        tool_calls_buffer: dict[int, dict[str, str]] = {}
        msg_buffer: list[str] = []
        finish_reason: str | None = None

        for chunk in stream:
            # 更新 finish_reason（只有最后一个 chunk 会有非 None 值）
            if chunk.finish_reason is not None:
                finish_reason = chunk.finish_reason

            # 处理普通文本（只在没有工具调用时出现）
            if chunk.content:
                msg_buffer.append(chunk.content)
                yield chunk.content  # 直接逐字输出

            # 处理工具调用增量
            if chunk.tool_call_deltas:
                for tc_delta in chunk.tool_call_deltas:
                    idx: int = tc_delta["index"]

                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {"id": "", "name": "", "arguments": ""}

                    # 累积字段
                    if tc_delta.get("id"):
                        tool_calls_buffer[idx]["id"] = tc_delta["id"]
                    if tc_delta.get("name"):
                        tool_calls_buffer[idx]["name"] = tc_delta["name"]
                    if tc_delta.get("arguments"):
                        tool_calls_buffer[idx]["arguments"] += tc_delta["arguments"]

        # 流结束后判断
        if finish_reason == "tool_calls":
            # 将缓冲中的 tool_calls 转换为 API 要求的格式
            for idx in sorted(tool_calls_buffer.keys()):
                tc = tool_calls_buffer[idx]
                tool_calls_list.append(
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],  # 注意：这里是 JSON 字符串，不是 dict
                        },
                    }
                )
