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

    if prompt == "/du":
        # display user inject prompt
        g = assistant_manager.dump_user_prompt(owner)
    elif prompt == "/da":
        # display all
        g = assistant_manager.dump_history(owner)
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
    elif prompt.startswith("/compress"):
        # 调试指令: 全局记忆压缩
        g = assistant_manager.auto_compress_memory()
    elif prompt.startswith("/set_memory "):
        args = prompt.removeprefix("/set_memory ")
        g = assistant_manager.set_memory(args, owner)
    elif prompt.startswith("/set_time "):
        args = prompt.removeprefix("/set_time ")
        g = assistant_manager.set_time(args, owner)
    elif prompt.startswith("/rumor"):
        # 调试指令: 全局生成流言
        g = assistant_manager.rumor_propagation(owner)
    elif prompt.startswith("/history "):
        args = prompt.removeprefix("/history ")
        g = assistant_manager.show_day_history(args, owner)
    elif prompt.startswith("/inject "):
        args = prompt.removeprefix("/inject ")
        inject_data, up = parse_switch_args(prompt)
        g = assistant_manager.inject(inject_data=inject_data, user_prompt=up, owner=owner)
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


def parse_switch_args(prompt) -> tuple[str, str]:
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


@llm_bp.post("/api/assistant/delete")
@authority_check()
def assistant_delete(owner: str):
    f: dict = request.get_json()
    num = int(f.get("num", "1"))
    return assistant_manager.delete(num, owner)
