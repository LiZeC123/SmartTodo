import json
from collections.abc import Callable, Iterator, Sequence
from datetime import datetime, timedelta

from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolUnionParam,
    ChatCompletionUserMessageParam,
)

from app.models.assistant import (
    AssistantModeType,
    AssistantTagType,
    Status,
    assistant_mode_str,
)
from app.models.exception import LLMIllegalStatusException
from app.models.memory import (
    KB,
)
from app.services.assistant_history import AssistantHistoryManager
from app.services.assistant_memory import AssistantMemoryManager
from app.services.config_manager import ConfigManager
from app.services.role_manager import RoleManager
from app.services.tomato_manager import TomatoRecordManager
from app.template.prompt import (
    AssistantSp,
    AutoAnswerPrompt,
    ContinueWritingPrompt,
    InjectRumorPrompt,
    RolePalyingSp,
)
from app.tools.llm import LLMClient
from app.tools.log import logger
from app.tools.time import (
    format_timedelta,
    get_datetime_from_str,
    get_hour_str_from,
    get_str_from_datetime,
    now,
    now_str,
    parse_befeore_time_str,
    today_begin,
)


class AssistantManager:
    def __init__(self, cm: ConfigManager, trm: TomatoRecordManager) -> None:
        self.role_manager = RoleManager()

        self.config_manager = cm
        self.llm_manager = LLMClient(cm)

        self.tomato_record_manager = trm
        self.item_manager = trm.item_manager
        self.history_manager = AssistantHistoryManager(self.item_manager.db)
        self.memory_manager = AssistantMemoryManager(
            self.item_manager.db, self.role_manager, self.llm_manager, self.history_manager
        )
        self.event_manager = self.item_manager.event_manager

        # 执行一些其他初始化逻辑
        self.print_check_info()

    def print_check_info(self):
        logger.info(f"当前是生产环境?: {self.config_manager.is_production()}")

    def make_system_prompt(self, status: Status) -> ChatCompletionSystemMessageParam:
        config = self.role_manager.get_role(name=status.assistant_name)
        desc = config.get_self_desc()
        if status.assistant_mode == AssistantModeType.RolePlaying:
            return ChatCompletionSystemMessageParam(role="system", content=RolePalyingSp.format(role_desc=desc))

        return ChatCompletionSystemMessageParam(role="system", content=AssistantSp.format(role_desc=desc))

    def get_history(self, owner: str) -> list[ChatCompletionMessageParam]:
        status = self.history_manager.query_or_init_status(owner)
        sp = self.make_system_prompt(status)
        memory = self.memory_manager.query_memory_detail(status.assistant_name, owner)
        start_time = self.memory_manager.query_msg_start_time(status.assistant_name, owner)
        records = self.history_manager.select_record_between(status.assistant_name, start_time, now(), owner)

        if not memory:
            return [sp] + [msg.to_openai() for msg in records]

        mp = ChatCompletionUserMessageParam(role="user", content=memory)
        return [sp, mp] + [msg.to_openai() for msg in records]

    def generate(self, owner: str, *, enable_tools=False) -> Iterator[str]:
        """流式生成回复：后台消费 LLM 流并保存，前台推送给客户端"""
        if not enable_tools:
            history = self.get_history(owner)
            stream = self.llm_manager.generate_stream(history)
            yield from self._consume_simple_stream(stream, owner)
        else:
            yield from self._consume_tool_stream(owner)

    def _consume_simple_stream(self, stream: Iterator[str], owner: str) -> Iterator[str]:
        """消费简单模式的流"""
        full_answer = []
        try:
            for token in stream:
                full_answer.append(token)
                yield token
        except GeneratorExit as e:
            logger.error(f"推送LLM模型消息到客户端中断: {e}")
            # 继续消费上游数据, 确保已经生成的内容依然可以落库
            for token in stream:
                full_answer.append(token)
        except Exception as e:
            # 发生其他异常时，先尝试发送错误信息（如果客户端还在）
            logger.error(f"推送LLM模型消息到客户端异常: {e}")
            yield str(e)
        finally:
            content = "".join(full_answer)
            self.history_manager.add_assistant_answer(content, owner)

    def _consume_tool_stream(self, owner: str) -> Iterator[str]:
        tool_desc, tool_map = self.make_tools(owner)

        while True:
            tool_calls_list = []
            full_answer = []
            history = self.get_history(owner)
            stream = self.llm_manager.generate_steam_with_tools(history, tool_desc, tool_calls_list)
            for token in stream:
                full_answer.append(token)
                yield token
            if not full_answer:
                return

            content = "".join(full_answer)
            if tool_calls_list:
                list_josn = json.dumps(tool_calls_list)
                self.history_manager.add_assistant_answer(content, owner, tool_call_list_json=list_josn)
                # 执行工具调用
                for tc in tool_calls_list:
                    name = tc["function"]["name"]
                    if name in tool_map:
                        result = tool_map[name](tc["function"]["arguments"])
                        self.history_manager.add_tool_call_msg(tc["id"], result, owner=owner)
                # 继续循环
            else:
                # 没有工具调用可以结束循环
                self.history_manager.add_assistant_answer(content, owner)
                return

    def make_tools(self, owner: str) -> tuple[Sequence[ChatCompletionToolUnionParam], dict[str, Callable[[str], str]]]:
        from app.services.assistant_tool import AssistantTool

        tool_manager = AssistantTool(self, owner)

        return tool_manager.collect()

    def chat(self, prompt: str, owner: str, *, inject_content: str = "") -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        config = self.role_manager.get_role(name=status.assistant_name)
        inject_content = self.make_user_inject_content(status, owner) if inject_content == "" else inject_content
        self.history_manager.add_user_prompt(prompt, inject_content, owner)
        yield from self.generate(owner, enable_tools=bool(config.enable_tools))

        length = self.history_manager.query_last_assistant_msg_length(owner)
        while status.auto_continue and length < status.auto_continue:
            self.history_manager.add_user_prompt("", ContinueWritingPrompt, owner)
            yield from self.generate(owner, enable_tools=bool(config.enable_tools))
            self.history_manager.merge_assistant_msg(owner)
            length = self.history_manager.query_last_assistant_msg_length(owner)

    def remake(self, owner: str) -> Iterator[str]:
        self.history_manager.remove_last_assistant(owner)
        last_user_msg = self.history_manager.remove_last_user(owner)
        if not last_user_msg:
            raise LLMIllegalStatusException("")

        return self.chat(last_user_msg.content, owner)

    def auto_answer(self, owner: str) -> Iterator[str]:
        self.history_manager.add_user_prompt("", AutoAnswerPrompt, owner)
        yield from self.generate(owner)
        msg = self.history_manager.remove_anto_answer_msg(owner)
        yield "\n\\n"
        yield from self.chat(msg, owner)

    def delete(self, num: int, owner: str) -> bool:
        if num < 1:
            return False

        for _ in range(num):
            self.history_manager.remove_last_pair(owner)
        return True

    def replace(self, prompt: str, owner: str) -> Iterator[str]:
        self.history_manager.remove_last_pair(owner)
        return self.chat(prompt, owner)

    def auto_switch(self, *, role_keyword: str, owner: str) -> Iterator[str]:
        config = self.role_manager.get_role(keyword=role_keyword)
        self.history_manager.switch(role_config=config, owner=owner)
        yield f"切换到角色: {config.name}"

    def change_mode(self, role_mode: int, owner: str) -> Iterator[str]:
        self.history_manager.change_mode(role_mode, owner)
        yield f"切换到模式: {assistant_mode_str(role_mode)}"

    def set_auto_continue(self, min_char_num: int, owner: str) -> Iterator[str]:
        self.history_manager.set_auto_continue(min_char_num, owner=owner)
        yield f"设置最小续写阈值为: {min_char_num} 个字符"

    def make_user_inject_content(self, status: Status, owner: str) -> str:
        # 扮演模式不注入任何系统相关的信息
        if status.assistant_mode == AssistantModeType.RolePlaying:
            return ""

        # 非扮演模式查询具体的状态信息
        # 当前番茄钟状态
        start = self.history_manager.get_last_assistant_mode_time(status)
        state = self.tomato_record_manager.get_tomato_state(owner=owner)
        content = f"番茄钟状态: {state}\n"

        # 事件信息, 可能没有事件
        # 如果已经跨越了1天时间, 则昨天产生的信息不再继续追加到当前会话中
        start = tb if (tb := today_begin()) > start else start
        event_info = self.get_event_info(owner, start)
        if event_info != "":
            content += "用户新增的事件记录:\n" + event_info

        return content

    def get_role_info_list(self) -> Iterator[str]:
        raw_list = self.role_manager.get_role_list()
        for role in raw_list:
            name = role.name
            desc = role.short_desc
            yield f"{name}: {desc}\n"

    def show_cost(self, owner: str) -> Iterator[str]:
        head = "角色: 记忆字符数+对话字符数（轮数）= 总字符数(预计token数)"
        report = [head]
        names = self.history_manager.get_recent_assistant_list(owner)
        for name in names:
            memory_cost = len(self.memory_manager.query_memory_detail(name, owner))
            start_time = self.memory_manager.query_msg_start_time(name, owner)
            records = self.history_manager.select_record_between(name, start_time, now(), owner)
            char_cost = sum(len(s) for r in records if (s := r.to_dump()))
            conv_cnt = len(records) // 2
            all_char_cost = memory_cost + char_cost
            token_cost = (memory_cost + char_cost) * 1.5
            delta_times = format_timedelta(now() - start_time)
            txt = f"{name:>8s}: {memory_cost / 1024:2.1f}KB+{char_cost // 1024:3d}KB({conv_cnt:3d}轮)={all_char_cost // 1024:3d}KB({token_cost / 1024:3.1f}K) / {delta_times} "
            report.append(txt)
        yield "\n".join(report)

        head = "\n\n当前角色成本明细:"
        report = [head]
        state = self.history_manager.query_or_init_status(owner)
        start_day = now() - timedelta(days=14)
        rows = self.history_manager.evalute_day_cost(state.assistant_name, start_day, owner)
        report.extend([f"{d}: {total_cnt / KB:6.2f} KB / {msg_cnt // 2:4d} Msg" for d, total_cnt, msg_cnt in rows])
        yield "\n".join(report)

    def show_memory(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        start_time = self.memory_manager.query_msg_start_time(status.assistant_name, owner)
        content = f"原始对话起始时间: {get_str_from_datetime(start_time)}\n"
        content += self.memory_manager.query_memory_detail(status.assistant_name, owner)
        yield content

    def show_last_reason(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        memory_reason = self.memory_manager.query_last_reason(status.assistant_name, owner)

        rumor_detail = self.memory_manager.query_rumor(owner)
        rumor_reason = rumor_detail.reason if rumor_detail else ""

        content = f"压缩记忆: \n{memory_reason}\n\n流言蜚语: \n {rumor_reason}"
        yield content

    def new_topic(self, owner: str) -> Iterator[str]:
        inject = "你需要根据现有的近期话题主动发起一个新话题"
        self.history_manager.add_user_prompt("", inject, owner, tag=AssistantTagType.NewTopic)
        yield from self.generate(owner)

    def set_memory(self, memory_type: str, content: str, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        if memory_type == "设定":
            self.memory_manager.stabilize_role_setting(
                content=content, assistant_name=status.assistant_name, owner=owner
            )
        elif memory_type == "偏好":
            self.memory_manager.stabilize_preference(content=content, assistant_name=status.assistant_name, owner=owner)

        yield from self.show_memory(owner)

    def set_time(self, time_str: str, owner: str) -> Iterator[str]:
        """设置原始聊天上下文起始时间, 支持待办事项截止日期相同格式的时间, 或者字符串'now'表示设置为当前时间"""
        if time_str == "now":
            content = now_str()
        else:
            t = parse_befeore_time_str(time_str)
            content = get_str_from_datetime(t)
        status = self.history_manager.query_or_init_status(owner)
        self.memory_manager.set_process_time(content=content, assistant_name=status.assistant_name, owner=owner)
        yield from self.show_memory(owner)

    def dump_memory(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        yield self.memory_manager.dump_memory_detail(status.assistant_name, owner)

    def dump_tool(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        msgs = self.history_manager.select_recent_tool_call_msgs(status.assistant_name, 3, owner)
        if not msgs:
            yield "最近没有工具调用记录"
            return

        lines: list[str] = []
        for i, msg in enumerate(msgs):
            lines.append(f"--- 工具调用 #{i + 1} ---")
            lines.append(f"时间: {get_str_from_datetime(msg.create_time)}")
            for tc in json.loads(msg.tool_call_list_json):
                name = tc["function"]["name"]
                args = tc["function"]["arguments"]
                lines.append(f"调用: {name}({args})")
                result = self.history_manager.select_tool_result_msg(tc["id"])
                if result:
                    lines.append(f"返回: {result.content}")
            lines.append("")
        content = "\n".join(lines)
        yield content

    def rumor(self, owner: str) -> Iterator[str]:
        yestoday = today_begin() - timedelta(days=1)
        yield "正在生成流言蜚语\n"
        self.memory_manager.rumor_propagation(yestoday, owner)
        rumor = self.memory_manager.query_rumor(owner)
        yield rumor.content if rumor else ""

    def rumor_propagation(self, target_keyword: str, owner: str) -> Iterator[str]:
        rumor_detail = self.memory_manager.query_rumor(owner)
        if not rumor_detail:
            yield "当前没有流言蜚语"
            return

        target = ""
        if target_keyword:
            target = f"用户要求你关注{target_keyword}相关的流言蜚语."

        inject_content = InjectRumorPrompt.format(target=target, rumor_text=rumor_detail.content)
        self.history_manager.add_user_prompt("", inject_content, owner, tag=AssistantTagType.Rumor)

        status = self.history_manager.query_or_init_status(owner)
        config = self.role_manager.get_role(name=status.assistant_name)
        yield from self.generate(owner, enable_tools=config.enable_tools)

    def inject(self, inject_data: str, user_prompt: str, owner: str) -> Iterator[str]:
        self.history_manager.add_user_prompt(user_prompt, inject_data, owner)
        yield from self.generate(owner)

    def __is_zero_tomoto_task(self, name: str) -> bool:
        # 打卡类任务可瞬间完成无需番茄钟.  午间和晚间任务不占用番茄钟
        keywords = ["打卡", "午间", "晚间"]
        return any(word in name for word in keywords)

    def get_event_info(self, owner: str, begin_time: datetime) -> str:
        content = ""
        # 新增番茄钟记录
        events = self.event_manager.get_event_log_after(begin_time, owner)
        for e in events:
            content += f"{get_hour_str_from(e.create_time)}: {e.msg}\n"

        return content

    def get_web_history(self, owner: str) -> list[dict]:
        status = self.history_manager.query_or_init_status(owner)
        start_time = self.memory_manager.query_msg_start_time(status.assistant_name, owner)
        records = self.history_manager.select_record_between(status.assistant_name, start_time, now(), owner)

        data_after = self.history_manager.to_web_json_list(records)
        div = [{"type": "divider", "label": "以上对话已压缩至记忆"}]

        data_before = self.history_manager.get_more_web_history(start_time, owner)
        if data_before:
            return data_before + div + data_after
        else:
            return data_after

    def get_more_web_history(self, end_time_str: str, owner: str) -> list[dict]:
        if end_time_str == "":
            return []

        end_time = get_datetime_from_str(end_time_str)
        return self.history_manager.get_more_web_history(end_time=end_time, owner=owner)

    def dump_user_prompt(self, owner: str) -> Iterator[str]:
        status = self.history_manager.query_or_init_status(owner)
        mode = assistant_mode_str(status.assistant_mode)
        config = self.role_manager.get_role(name=status.assistant_name)
        content = (
            f"【当前状态信息】\n角色名: {status.assistant_name}\n角色模式: {mode}\n角色描述: {config.short_desc}\n"
        )

        rumor = self.memory_manager.query_rumor(owner)
        rumor_text = rumor.content if rumor else ""
        content += f"\n【流言蜚语】\n{rumor_text}\n"

        records = self.history_manager.select_inject_history(status.assistant_name, 4, owner)
        content += "\n【最近几条注入信息】\n"
        content += "\n".join([r.system_inject_content for r in reversed(records)])

        to_inject_content = self.make_user_inject_content(status, owner)
        content += f"\n\n【即将注入的信息】\n{to_inject_content}\n"

        yield content

    def auto_update_memory(self):
        if not self.config_manager.is_production():
            logger.info("非生产环境, 取消记忆压缩任务执行")
            return

        users = self.config_manager.get_all_users()
        start_time = today_begin() - timedelta(days=1)
        for user in users:
            # 检查该用户所有助理的历史对话长度, 更新满足要求的助理的记忆
            for role in self.history_manager.get_recent_assistant_list(user):
                config = self.role_manager.get_role(name=role)
                self.memory_manager.update_long_term_memory(config=config, owner=user)
            # 基于已经更新的日记, 计算用户行为轨迹, 作为流言蜚语传播的素材
            self.memory_manager.rumor_propagation(start_time, user)

    def debug_update_memory(self) -> Iterator[str]:
        yield "正在执行记忆压缩操作\n"
        self.auto_update_memory()
        yield "记忆压缩完毕\n"
