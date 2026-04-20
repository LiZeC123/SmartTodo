
from typing import Any, Generator, List

from app.services.config_manager import ConfigManager

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

class LLMClient:
    def __init__(self, config_manager: ConfigManager) -> None:
        base_url, api_key = config_manager.get_llm_info()
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate_stream(self, history: List[ChatCompletionMessageParam]) -> Generator[str, Any, None]:
        response = self.client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3.2",
            messages=history,
            stream=True,
        )

        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                data = chunk.choices[0].delta.content
                yield data