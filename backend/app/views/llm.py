import json
from collections.abc import Iterator

from flask import Blueprint, Response, request

from app import assistant_manager, db
from app.models.assistant import parse_assistant_mode
from app.tools.log import logger
from app.views.authority import authority_check

llm_bp = Blueprint("llm", __name__)


@llm_bp.post("/api/stream/assistant/chat")
@authority_check()
def assistant_chat_stream(owner: str):
    f: dict = request.get_json()
    prompt: str = f.get("prompt", "")

    g: Iterator[str]
    if prompt == "/info":
        # display user inject prompt
        g = assistant_manager.dump_user_prompt(owner)
    elif prompt == "/re":
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
    elif prompt == "/dump_memory":
        g = assistant_manager.dump_memory(owner)
    elif prompt == "/dump_tool":
        g = assistant_manager.dump_tool(owner)
    elif prompt == "/debug_compress":
        g = assistant_manager.debug_update_memory()
    elif prompt == "/auto_answer":
        g = assistant_manager.auto_answer(owner)
    elif prompt == "/rumor":
        g = assistant_manager.rumor_propagation(owner)
    elif prompt.startswith("/switch "):
        # 切换助理角色, 自动维持上一次使用的模式
        args = prompt.removeprefix("/switch ")
        g = assistant_manager.auto_switch(role_keyword=args, owner=owner)
    elif prompt.startswith("/change_mode "):
        # 切换当前助理角色的模式
        args = prompt.removeprefix("/change_mode ")
        g = assistant_manager.change_mode(role_mode=parse_assistant_mode(args), owner=owner)
    elif prompt.startswith("/set_auto_continue "):
        args = prompt.removeprefix("/set_auto_continue ").strip()
        g = assistant_manager.set_auto_continue(min_char_num=int(args), owner=owner)
    elif prompt.startswith("/rc "):
        # replace content
        args = [arg for arg in prompt.strip().split() if arg]
        g = assistant_manager.replace(args[1], owner)
    elif prompt.startswith("/set_memory "):
        args = prompt.strip().split(maxsplit=2)
        g = assistant_manager.set_memory(args[1].strip(), args[2].strip(), owner)
    elif prompt.startswith("/set_time "):
        args = prompt.removeprefix("/set_time ").strip()
        g = assistant_manager.set_time(args, owner)
    # elif prompt.startswith("/rumor"):
    #     # 调试指令: 注入流言, 可指定特别关注的角色, 也可以让模型自行决定
    #     args = prompt.removeprefix("/rumor ").strip()
    #     g = assistant_manager.rumor_propagation(args, owner)
    # elif prompt.startswith("/make_rumor"):
    #     g = assistant_manager.rumor(owner)
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


    # 这里Return后此接口执行完毕, 会判定有无异常并决定是否提交数据库, 因此此处无需手动commit
    # 但迭代器执行完毕后可能会产生一些其他数据库操作, 这一部分操作在统一commit操作之后, 因此需要额外手动提交
    # 否则相关操作一直持有数据库锁, 将导致异常
    return Response(
        generate_sse_from(g),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
        },
    )


def generate_sse_from(g: Iterator[str]):
    """
    返回一个新迭代器, 对原迭代器的内容进行SSE格式封装
    """
    it = iter(g)
    try:
        prev = next(it)  # 尝试获取第一个元素
    except StopIteration:
        return  # 迭代器为空，直接返回（空生成器）

    try:
        for curr in it:  # 遍历剩下的元素
            # 当前 prev 不是最后一个, done 为False
            yield f"data: {json.dumps({'text': prev, 'done': False})}\n\n"
            prev = curr
        # 循环结束后，prev 是原迭代器的最后一个元素
        yield f"data: {json.dumps({'text': prev, 'done': True})}\n\n"
    except Exception as e:
        logger.exception(f"SSE封装过程出现异常: {e}")
        yield f"data: {json.dumps({'text': str(e), 'done': True})}\n\n"
    finally:
        # 确保任何情况下, 请求处理完毕都执行了提交操作.
        db.commit()


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
    end_time_str = f.get("before_time", "")
    return assistant_manager.get_more_web_history(end_time_str, owner)


@llm_bp.post("/api/assistant/delete")
@authority_check()
def assistant_delete(owner: str):
    f: dict = request.get_json()
    num = int(f.get("num", "1"))
    return assistant_manager.delete(num, owner)
