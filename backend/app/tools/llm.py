
from typing import Any, Callable, Dict, Generator, Iterable, List

from app.services.config_manager import ConfigManager

from openai import OpenAI
from openai.types.chat import ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionToolMessageParam, ChatCompletionToolUnionParam

class LLMClient:
    def __init__(self, config_manager: ConfigManager) -> None:
        base_url, api_key, model_name = config_manager.get_llm_info()
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def generate_stream(self, history: List[ChatCompletionMessageParam]) -> Generator[str, Any, None]:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=history,
            stream=True,
            extra_body={"thinking": {"type": "disabled"}}
        )

        for chunk in response:
            if len(chunk.choices) > 0 and chunk.choices[0].delta.content is not None:
                data = chunk.choices[0].delta.content
                yield data

    def generate_one_shot(self, prompt:str):
        """单次非流式请求模型, 返回思考内容和模型回复"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt},
            ],
            reasoning_effort="xhigh",
            extra_body={"thinking": {"type": "enabled"}}
        )
        
        reasoning_content = response.choices[0].message.reasoning_content # type: ignore
        content = response.choices[0].message.content
        return reasoning_content, content
        
                
    def generate_steam_with_tools(self, history: List[ChatCompletionMessageParam], tools: Iterable[ChatCompletionToolUnionParam],
                                  tool_map: Dict[str, Callable[[str], str]]) -> Generator[str, Any, None]:
        response = self.client.chat.completions.create(
            model=self.model_name, messages=history, stream=True, tools=tools,
            extra_body={"thinking": {"type": "disabled"}}
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
                yield delta.content # 直接逐字输出

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
                            tool_calls_buffer[idx][
                                "arguments"
                            ] += tool_call_delta.function.arguments
    
        # 流结束后判断
        if finish_reason == "tool_calls":
            # ========== 关键修复点：构造完整的 assistant 消息（包含 tool_calls） ==========
            # 1. 将缓冲中的 tool_calls 转换为 API 要求的格式
            tool_calls_list = []
            for idx in sorted(tool_calls_buffer.keys()):
                tc = tool_calls_buffer[idx]
                tool_calls_list.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"]   # 注意：这里是 JSON 字符串，不是 dict
                    }
                })

            # 2. 构造 assistant 消息，必须同时包含可能的文本（如果有）和 tool_calls
            #    注意：当有 tool_calls 时，content 通常为 None（或空字符串），但如果你之前输出过文本，可以保留，不过一般来说模型不会在 tool_calls 的同时输出 content
            assistant_msg = ChatCompletionAssistantMessageParam(
                role="assistant",
                content="".join(msg_buffer) if msg_buffer else None,
                tool_calls=tool_calls_list   # 关键：加上 tool_calls 字段
            )
            history.append(assistant_msg)

            # 3. 执行所有工具调用并添加 tool 消息
            for tc in tool_calls_list:
                name = tc["function"]["name"]
                if name in tool_map:
                    # 注意：arguments 是 JSON 字符串，如果你的工具函数需要 dict，可以 json.loads(tc["function"]["arguments"])
                    result = tool_map[name](tc["function"]["arguments"])
                    history.append(
                        ChatCompletionToolMessageParam(
                            role="tool",
                            tool_call_id=tc["id"],
                            content=result
                        )
                    )

            # 4. 发起第二轮流式请求，输出最终回答（这里可以继续 yield）
            second_response = self.client.chat.completions.create(
                model=self.model_name, messages=history, stream=True, tools=tools,   # 如果后续不再需要工具调用，可以不带 tools
                extra_body={"thinking": {"type": "disabled"}}
            )
            for chunk in second_response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content         