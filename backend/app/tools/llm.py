from collections.abc import Generator, Iterable
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


class LLMClient:
    def __init__(self, config_manager: ConfigManager) -> None:
        base_url, api_key, model_name = config_manager.get_llm_info()
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name: str = model_name

        base_url, api_key, model_name = config_manager.get_tool_llm_info()
        self.simple_client = OpenAI(api_key=api_key, base_url=base_url)
        self.simple_model_name: str = model_name
        logger.info(f"主模型名: {self.model_name} 简单模型名: {self.simple_model_name}")

        self.history_space: dict[str, list[ChatCompletionMessageParam]] = {}

    def generate_stream(self, history: list[ChatCompletionMessageParam]) -> Generator[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model_name, messages=history, stream=True, extra_body=thinking_disable
        )

        for chunk in response:
            if len(chunk.choices) > 0 and chunk.choices[0].delta.content is not None:
                data = chunk.choices[0].delta.content
                yield data

    def generate_one_shot(self, prompt: str, *, thinking=True, simple_client=False):
        client, model_name, extra_body = self.get_client_and_body(thinking, simple_client)

        """单次非流式请求模型, 返回思考内容和模型回复"""
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt},
            ],
            # 由于max模式Token消耗极大, 因此考虑先使用默认的模式
            # reasoning_effort="max", # type: ignore
            extra_body=extra_body,
        )

        reasoning_content = response.choices[0].message.reasoning_content if thinking else ""  # type: ignore
        content = response.choices[0].message.content
        return reasoning_content, content

    def generate_one_shot_with_history(
        self, prompt: str, history_tag: str, *, thinking=True, simple_client=False
    ) -> str:
        client, model_name, extra_body = self.get_client_and_body(thinking, simple_client)
        history_list = self.get_history(history_tag)
        history_list.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model_name,
            messages=history_list,
            extra_body=extra_body,
        )

        content = response.choices[0].message.content
        if content:
            history_list.append({"role": "assistant", "content": content})
            return content
        return "查询结果为空"

    def get_client_and_body(self, thinking: bool, simple_client: bool) -> tuple[OpenAI, str, dict]:
        client = self.simple_client if simple_client else self.client
        mode_name = self.simple_model_name if simple_client else self.model_name
        extra_body = thinking_enable if thinking else thinking_disable
        return client, mode_name, extra_body

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
        response = self.client.chat.completions.create(
            model=self.model_name, messages=history, stream=True, tools=tools, extra_body=thinking_disable
        )

        tool_calls_buffer = {}
        msg_buffer = []
        finish_reason = None

        for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason  # 最后一个chunk会包含

            # 处理普通文本（只在没有工具调用时出现）
            if delta.content:
                msg_buffer.append(delta.content)
                yield delta.content  # 直接逐字输出

            # 处理工具调用增量
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx = tool_call_delta.index  # 并行调用时的索引

                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {"id": "", "name": "", "arguments": ""}

                    # 累积字段
                    if tool_call_delta.id:
                        tool_calls_buffer[idx]["id"] = tool_call_delta.id
                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            tool_calls_buffer[idx]["name"] = tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            tool_calls_buffer[idx]["arguments"] += tool_call_delta.function.arguments

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
