from typing import Dict, List

from flask import Blueprint, request, Response
from sqlalchemy import Tuple

from app import assistant_manager
from app.models.assistant import AssistantModeType
from app.views.authority import authority_check

llm_bp = Blueprint('llm', __name__)


@llm_bp.post('/api/stream/assistant/chat')
@authority_check()
def assistant_chat_stream(owner: str):
    f: Dict = request.get_json()
    prompt: str = f.get('prompt', '')
    
    if prompt == '/du':
        # display user inject prompt
        g = assistant_manager.dump_user_prompt(owner)
    elif prompt == '/da':
        # display all
        g = assistant_manager.dump_history(owner)
    elif prompt == '/rk':
        # remake answer
        g = assistant_manager.remake(owner)
    elif prompt == "/role_list":
        g = assistant_manager.get_role_info_list()
    elif prompt == '/show_cost':
        g = assistant_manager.show_cost(owner)
    elif prompt == '/show_memory':
        g = assistant_manager.show_memory(owner)    
    elif prompt == '/compress':
        g = assistant_manager.compress_memory(owner)
    elif prompt == '/reason':
        g = assistant_manager.show_last_reason(owner)
    elif prompt.startswith("/switch_work "):
        # 切换指定角色到聊天模式
        role_keyword, user_prompt = parse_switch_args(prompt)
        g = assistant_manager.switch(role_keyword=role_keyword, role_mode=AssistantModeType.Assistant, prompt=user_prompt, owner=owner)
    elif prompt.startswith("/switch_talk "):
        # 切换指定角色到扮演模式
        role_keyword, user_prompt = parse_switch_args(prompt)
        g = assistant_manager.switch(role_keyword=role_keyword, role_mode=AssistantModeType.RolePlaying, prompt=user_prompt, owner=owner)
    elif prompt.startswith("/rc "):
        # replace content
        args = [arg for arg in prompt.strip().split() if arg]
        g = assistant_manager.replace(args[1], owner)
    elif prompt.startswith("/rs"):
        # reset 
        args = [arg for arg in prompt.strip().split() if arg]
        if len(args) >= 2:
            g = assistant_manager.reset(owner, args[1])
        else:
            g = assistant_manager.reset(owner)
    else:
        g = assistant_manager.chat(prompt, owner)

    return Response(g, mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # 禁用Nginx缓冲
        }
    )


def parse_switch_args(prompt) -> tuple[str, str]:
    "解析角色名关键词和用户的prompt"
    args: List[str] = [arg for arg in prompt.strip().split() if arg]
    if len(args) >= 3:
        return args[1],args[2]
    elif len(args) == 2:
        return args[1],""
    else:
        return "", ""



@llm_bp.post('/api/assistant/history')
@authority_check()
def assistant_history(owner: str):
    return assistant_manager.get_web_history(owner)


@llm_bp.post('/api/assistant/delete')
@authority_check()
def assistant_delete(owner: str):
    return assistant_manager.delete(owner)
