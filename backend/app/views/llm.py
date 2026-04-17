from typing import Dict

from flask import Blueprint, request, Response

from app import assistant_manager
from app.views.authority import authority_check

llm_bp = Blueprint('llm', __name__)


@llm_bp.post('/api/stream/assistant/chat')
@authority_check()
def chat_stream(owner: str):
    f: Dict = request.get_json()
    prompt = f.get('prompt', '')
    
    return Response(
        assistant_manager.chat(prompt, owner),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # 禁用Nginx缓冲
        }
    )


# Personal Assistant


# 1. 查询历史对话
# 2. 发送对话, 返回回复文本
# 3. 控制操作
# 4. 初始化生成与重新生成



def personal_assistant_history():
    pass

def personal_assistant_chat():
    pass


