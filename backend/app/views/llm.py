from flask import Blueprint, Response, request

from app import assistant_manager
from app.models.assistant import parse_assistant_mode
from app.views.authority import authority_check

llm_bp = Blueprint("llm", __name__)


@llm_bp.post("/api/stream/assistant/chat")
@authority_check()
def assistant_chat_stream(owner: str):
    f: dict = request.get_json()
    prompt: str = f.get("prompt", "")

    if prompt == "/info":
        # display user inject prompt
        g = assistant_manager.dump_user_prompt(owner)
    elif prompt == "/rk":
        # remake answer
        g = assistant_manager.remake(owner)
    elif prompt == "/role_list":
        g = assistant_manager.get_role_info_list()
    elif prompt == "/cost":
        g = assistant_manager.show_cost(owner)
    elif prompt == "/memory":
        g = assistant_manager.show_memory(owner)
    elif prompt == "/reason":
        g = assistant_manager.show_last_reason(owner)
    elif prompt == "/topic":
        g = assistant_manager.new_topic(owner)
    elif prompt.startswith("/switch "):
        # 切换助理角色, 自动维持上一次使用的模式
        args = prompt.removeprefix("/switch ")
        g = assistant_manager.auto_switch(role_keyword=args, owner=owner)
    elif prompt.startswith("/change_mode "):
        # 切换当前助理角色的模式
        args = prompt.removeprefix("/change_mode ")
        g = assistant_manager.change_mode(role_mode=parse_assistant_mode(args), owner=owner)
    elif prompt.startswith("/rc "):
        # replace content
        args = [arg for arg in prompt.strip().split() if arg]
        g = assistant_manager.replace(args[1], owner)
    elif prompt.startswith("/set_memory "):
        args = prompt.strip().split(maxsplit=2)
        g = assistant_manager.set_memory(args[1], args[2], owner)
    elif prompt.startswith("/set_time "):
        args = prompt.removeprefix("/set_time ")
        g = assistant_manager.set_time(args, owner)
    elif prompt.startswith("/rumor"):
        # 调试指令: 注入流言
        g = assistant_manager.rumor_propagation(owner)
    elif prompt.startswith("/inject "):
        args = prompt.removeprefix("/inject ")
        inject_data, up = parse_switch_args(prompt)
        g = assistant_manager.inject(inject_data=inject_data, user_prompt=up, owner=owner)
    elif prompt.startswith("/"):
        # 指令兜底分支, 如果没有匹配上任何其他指令, 则视为/topic指令
        # 避免输入一个未知的指令给模型, 让模型错误的回答
        g = assistant_manager.new_topic(owner)
    else:
        g = assistant_manager.chat(prompt, owner)

    return Response(
        g,
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
        },
    )


def parse_switch_args(prompt: str) -> tuple[str, str]:
    "解析角色名关键词和用户的prompt"
    args: list[str] = [arg for arg in prompt.strip().split() if arg]
    if len(args) >= 3:
        return args[1], args[2]
    elif len(args) == 2:
        return args[1], ""
    else:
        return "", ""


@llm_bp.post("/api/assistant/history")
@authority_check()
def assistant_history(owner: str):
    return assistant_manager.get_web_history(owner)

@llm_bp.post("/api/assistant/history/more")
@authority_check()
def more_assistant_history(owner: str):
    f: dict = request.get_json()
    end_time_str = f.get('before_time', '')
    return assistant_manager.get_more_web_history(end_time_str, owner)

@llm_bp.post("/api/assistant/delete")
@authority_check()
def assistant_delete(owner: str):
    f: dict = request.get_json()
    num = int(f.get("num", "1"))
    return assistant_manager.delete(num, owner)
