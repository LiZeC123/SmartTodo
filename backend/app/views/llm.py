from typing import Dict

from flask import Blueprint, request, Response

from app import assistant_manager
from app.views.authority import authority_check

llm_bp = Blueprint('llm', __name__)


@llm_bp.post('/api/stream/assistant/chat')
@authority_check()
def assistant_chat_stream(owner: str):
    f: Dict = request.get_json()
    prompt: str = f.get('prompt', '')
    
    if prompt == "/remake":
        g = assistant_manager.remake(owner)
    elif prompt.startswith("/replace "):
        g = assistant_manager.replace(prompt[9:], owner)
    elif prompt == "/dump":
        g = assistant_manager.dump_history(owner)
    else:
        g = assistant_manager.chat(prompt, owner)
    
    
    return Response(g, mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # 禁用Nginx缓冲
        }
    )


@llm_bp.post('/api/assistant/history')
@authority_check()
def assistant_history(owner: str):
    return assistant_manager.get_web_history(owner)


@llm_bp.post('/api/assistant/delete')
@authority_check()
def assistant_delete(owner: str):
    return assistant_manager.delete(owner)

@llm_bp.post('/api/assistant/reset')
@authority_check()
def assistant_reset(owner: str):
    f: Dict = request.get_json()
    role_keyword = str(f.get("keyword", "")).strip()
    return assistant_manager.reset(owner, role_keyword=role_keyword)
