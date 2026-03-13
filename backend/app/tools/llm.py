import json
from typing import Any, Generator

from openai import OpenAI


def generate_stream(client: OpenAI, prompt: str)-> Generator[str, Any, None]:
    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3.2",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                data = chunk.choices[0].delta.content
                # 格式化SSE数据
                yield f"data: {json.dumps({'text': data, 'done': False})}\n\n"
        
        # 发送结束标记
        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
