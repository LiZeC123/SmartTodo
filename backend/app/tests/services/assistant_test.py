from collections.abc import Iterator

from app.models.assistant import AssistantModeType, AssistantType, History
from app.services.assistant import AssistantManager
from app.services.assistant_tool import AssistantTool
from app.services.config_manager import ConfigManager
from app.services.event_log_manager import EventManager
from app.services.item_manager import ItemManager
from app.services.tomato_manager import TomatoManager, TomatoRecordManager
from app.tests.services.make_db import make_new_db
from app.tests.tools.llm_mock import MockLLMProvider
from app.tools.llm import StreamChunk
from app.tools.time import now

owner = "user"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _consume(g: Iterator[str]) -> str:
    """消费 generator 返回拼接字符串"""
    return "".join(list(g))


def _db_msg_count(am: AssistantManager, owner: str) -> int:
    """查询指定用户在 DB 中的消息总数"""
    status = am.history_manager.query_or_init_status(owner)
    start = am.memory_manager.query_msg_start_time(status.assistant_name, owner)
    records = am.history_manager.select_record_between(status.assistant_name, start, now(), owner)
    return len(records)


def _db_msgs(am: AssistantManager, owner: str) -> list[History]:
    """查询指定用户在 DB 中的所有消息"""
    status = am.history_manager.query_or_init_status(owner)
    start = am.memory_manager.query_msg_start_time(status.assistant_name, owner)
    return list(am.history_manager.select_record_between(status.assistant_name, start, now(), owner))


db = make_new_db()
event_manager = EventManager(db)
item_manager = ItemManager(event_manager)
tomato_manager = TomatoManager(item_manager)
tomato_record_manager = TomatoRecordManager(tomato_manager)
config_manager = ConfigManager()

assistant_manager = AssistantManager(config_manager, tomato_record_manager)
assistant_tool = AssistantTool(assistant_manager, owner)


# 替换 LLMClient 的 provider，阻断真实 LLM 调用。
# memory_manager.client 和 llm_manager 是同一对象引用，替换 provider 同时生效。
mock_provider = MockLLMProvider()
assistant_manager.llm_manager.provider = mock_provider
assistant_manager.llm_manager.simple_provider = MockLLMProvider(model_name="mock-simple-model")


def test_basic_stream():
    """流式生成：mock 返回多 chunk，输出拼接正确，结果落库"""
    mock_provider.register_stream(
        "hello",
        [StreamChunk(content="Hel"), StreamChunk(content="lo"), StreamChunk(content="!")],
    )
    # 先添加一个 user 消息使得 get_history 有内容
    assistant_manager.history_manager.add_user_prompt("hello", "自定义注入", owner)

    result = _consume(assistant_manager.generate(owner))

    assert result == "Hello!"
    # 验证 assistant 消息落库
    msgs = _db_msgs(assistant_manager, owner)
    assistant_msgs = [m for m in msgs if m.role == AssistantType.Assistant]
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0].content == "Hello!"

    # 删除添加的消息, 使数据库状态复原
    assert assistant_manager.history_manager.remove_last_pair(owner)


def test_chat() -> None:
    """基本对话：user 和 assistant 消息均落库"""
    mock_provider.register_stream("你好", [StreamChunk(content="你好呀！")])
    assert _consume(assistant_manager.change_mode(AssistantModeType.RolePlaying, owner))
    assert _consume(assistant_manager.auto_switch(role_keyword="some", owner=owner))
    result = _consume(assistant_manager.chat("你好", owner))

    assert result == "你好呀！"
    msgs = _db_msgs(assistant_manager, owner)
    assert len(msgs) == 2  # user + assistant
    assert msgs[0].role == AssistantType.User
    assert msgs[0].content == "你好"
    assert msgs[1].role == AssistantType.Assistant
    assert msgs[1].content == "你好呀！"

    am = assistant_manager
    _consume(am.show_cost(owner))
    _consume(am.show_memory(owner))
    _consume(am.show_last_reason(owner))
    _consume(am.dump_memory(owner))
    _consume(am.dump_tool(owner))
    _consume(am.dump_user_prompt(owner))

    # 按照相反的顺序应该能够删除
    assert assistant_manager.history_manager.remove_last_assistant(owner)
    assert assistant_manager.history_manager.remove_last_user(owner)


def test_auto_continue_triggered() -> None:
    """auto_continue 开启且回复过短时，触发续写循环并 merge"""
    # 设置阈值为 50 字符，mock 返回的首次回复仅 2 字符 → 触发续写
    assistant_manager.history_manager.set_auto_continue(50, owner)

    # 首次回复很短（2 字符）
    mock_provider.register_stream("问题", [StreamChunk(content="AB")])
    # 续写轮次：匹配 ContinueWritingPrompt 中的子串 "继续输出后续内容"
    mock_provider.register_stream("继续输出后续内容", [StreamChunk(content="CDEFGHIJ" * 6)])  # 48 字符

    result = _consume(assistant_manager.chat("问题", owner))

    # merge 后 content = "AB" + "CDEFGHIJ"*6 = 50 字符，满足阈值
    assert len(result) >= 50
    assert result.startswith("AB")
    assert "CDEFGHIJ" in result

    # DB 中应只有 2 条（user + merged assistant），
    # 因为 auto_continue 中间消息已被 merge_assistant_msg 清理
    msgs = _db_msgs(assistant_manager, owner)
    user_msgs = [m for m in msgs if m.role == AssistantType.User]
    assert len(user_msgs) == 1
    assert user_msgs[0].content == "问题"

    assert assistant_manager.delete(1, owner)


def test_auto_continue_multi_loop() -> None:
    """auto_continue 多轮循环：每轮回复都短于阈值，直到累计足够长"""
    assistant_manager.history_manager.set_auto_continue(30, owner)

    # 每轮只返回 5 字符，远低于 30 阈值
    mock_provider.register_stream("反复", [StreamChunk(content="aaaaa")])
    # 续写轮也返回短内容（走默认的短回复）
    mock_provider.register_stream("继续输出后续内容", [StreamChunk(content="bbbbb")])

    result = _consume(assistant_manager.chat("反复", owner))

    # 多轮 merge 后最终长度 >= 30（5+5+5+5...至少 6 轮）
    assert len(result) >= 30
    # DB 中应只有 user + merged assistant
    assert _db_msg_count(assistant_manager, owner) == 2
    assert assistant_manager.delete(1, owner)


def test_auto_continue_disabled_by_default() -> None:
    """默认 auto_continue=0，不触发续写循环"""
    mock_provider.register_stream("hi", [StreamChunk(content="Hi")])

    _consume(assistant_manager.chat("hi", owner))

    # 只有 user + assistant，没有额外的续写消息
    assert _db_msg_count(assistant_manager, owner) == 2
    assert assistant_manager.delete(1, owner)


# def test_remake_basic() -> None:
#     """chat 后 remake：删除旧回复，用原 prompt 重新生成"""
#     # 第一轮 chat
#     mock_provider.register_stream("原始问题", [StreamChunk(content="旧回答")])
#     _consume(assistant_manager.chat("原始问题", owner))

#     # 注册新回答（同一 prompt）
#     mock_provider.register_stream("原始问题", [StreamChunk(content="新回答")])

#     result = _consume(assistant_manager.remake(owner))

#     assert result == "新回答"
#     msgs = _db_msgs(assistant_manager, owner)
#     # 只有 user("原始问题") + assistant("新回答")
#     assert len(msgs) == 2
#     assert msgs[0].content == "原始问题"
#     assert msgs[1].content == "新回答"


# def test_no_history_raises() -> None:
#     """无历史记录时 remake 抛出 LLMIllegalStatusException"""
#     with pytest.raises(LLMIllegalStatusException):
#         _consume(assistant_manager.remake(owner))


# def test_preserves_original_prompt() -> None:
#     """remake 重新生成时使用与原 chat 相同的 prompt"""
#     mock_provider.register_stream("保留这个提示词", [StreamChunk(content="回复1")])
#     _consume(assistant_manager.chat("保留这个提示词", owner))

#     mock_provider.register_stream("保留这个提示词", [StreamChunk(content="回复2")])
#     _consume(assistant_manager.remake(owner))

#     msgs = _db_msgs(assistant_manager, owner)
#     user_msgs = [m for m in msgs if m.role == AssistantType.User]
#     assert len(user_msgs) == 1
#     assert user_msgs[0].content == "保留这个提示词"


# def test_after_tool_call_remake_succeeds() -> None:
#     """工具调用后 remake：remove_last_assistant 正确删除整个工具调用块

#     模拟 DB 中的消息序列：
#         user: "北京天气怎么样"
#         assistant: (tool_calls, content="")   ← 属于助手回复
#         tool: (call_1 结果)                    ← 属于助手回复
#         assistant: "北京今天晴天"               ← 属于助手回复

#     remove_last_assistant 应扫描删除全部 3 条非 user 消息，
#     remove_last_user 找到 user 消息并删除，remake 正常执行。
#     """
#     am = assistant_manager
#     am.history_manager.add_user_prompt("北京天气怎么样", "", owner)
#     am.history_manager.add_assistant_answer(
#         "",
#         owner,
#         tool_call_list_json='[{"id":"call_1","type":"function","function":{"name":"weather","arguments":"{}"}}]',  # pyright: ignore[reportArgumentType]
#     )
#     am.history_manager.add_tool_call_msg("call_1", "晴天, 25°C", owner=owner)
#     am.history_manager.add_assistant_answer("北京今天晴天", owner)

#     # 注册 remake 后 chat 所需的流式响应
#     mock_provider.register_stream("北京天气怎么样", [StreamChunk(content="新回复：北京晴天")])

#     result = _consume(am.remake(owner))

#     assert result == "新回复：北京晴天"
#     # DB 中应只有 2 条：user + 新 assistant
#     msgs = _db_msgs(am, owner)
#     assert len(msgs) == 2
#     assert msgs[0].role == AssistantType.User
#     assert msgs[0].content == "北京天气怎么样"
#     assert msgs[1].role == AssistantType.Assistant
#     assert msgs[1].content == "新回复：北京晴天"


# def test_remove_last_assistant_merges_tool_content() -> None:
#     """remove_last_assistant 将工具调用块的多条消息内容合并返回"""
#     am = assistant_manager
#     am.history_manager.add_user_prompt("查询", "", owner)
#     am.history_manager.add_assistant_answer("让我查一下", owner)
#     am.history_manager.add_tool_call_msg("call_x", "结果数据", owner=owner)
#     am.history_manager.add_assistant_answer("查到了：结果数据", owner)

#     merged = am.history_manager.remove_last_assistant(owner)

#     assert merged is not None
#     # 内容按时间顺序拼接：早 → 晚
#     assert merged.content == "让我查一下结果数据查到了：结果数据"
#     assert merged.role == AssistantType.Assistant


def test_remake():
    _consume(assistant_manager.chat("你好", owner))
    assistant_manager.remake(owner)
    _consume(assistant_manager.auto_answer(owner))
    _consume(assistant_manager.new_topic(owner))


def test_tool_collect():
    metadata_list, method_dict = assistant_tool.collect()
    assert metadata_list
    assert method_dict


def test_call_command():
    am = assistant_manager
    _consume(am.set_memory("设定", "123", owner))
    _consume(am.set_memory("偏好", "123", owner))

    _consume(am.set_time("now", owner))


def test_inject():
    _consume(assistant_manager.inject("注入自定义信息", "用户输入", owner))


def test_web_history():
    am = assistant_manager
    am.get_web_history(owner)
    am.get_more_web_history("2006-01-02 15:04:05", owner)
    am.get_more_web_history("", owner)


def test_rumor_and_memory():
    am = assistant_manager
    _consume(am.rumor_propagation(owner))
    am.auto_update_memory()
