"""AssistantManager 单元测试 —— generate / chat / remake

使用 test DB 替换数据层，使用 MockLLMProvider 替换 LLM 调用层。
"""

from collections.abc import Iterator

import pytest

from app.models.assistant import AssistantType, History
from app.models.exception import LLMIllegalStatusException
from app.services.assistant import AssistantManager
from app.services.config_manager import ConfigManager
from app.services.event_log_manager import EventManager
from app.services.item_manager import ItemManager
from app.services.tomato_manager import TomatoManager, TomatoRecordManager
from app.tests.services.make_db import make_new_db
from app.tests.tools.llm_mock import MockLLMProvider
from app.tools.llm import StreamChunk
from app.tools.time import now

OWNER = "test_user"


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


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
def mock_simple_provider() -> MockLLMProvider:
    return MockLLMProvider(model_name="mock-simple-model")


@pytest.fixture
def assistant_manager(mock_provider: MockLLMProvider, mock_simple_provider: MockLLMProvider) -> AssistantManager:
    """构造 AssistantManager，注入 mock provider 替换真实 LLM 调用"""
    db = make_new_db()
    event_manager = EventManager(db)
    item_manager = ItemManager(event_manager)
    tomato_manager = TomatoManager(item_manager)
    tomato_record_manager = TomatoRecordManager(tomato_manager)
    config_manager = ConfigManager()

    am = AssistantManager(config_manager, tomato_record_manager)

    # 替换 LLMClient 的 provider，阻断真实 LLM 调用。
    # memory_manager.client 和 llm_manager 是同一对象引用，替换 provider 同时生效。
    am.llm_manager.provider = mock_provider
    am.llm_manager.simple_provider = mock_simple_provider

    return am


# ===================================================================
# generate
# ===================================================================


class TestGenerate:
    def test_basic_stream(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """流式生成：mock 返回多 chunk，输出拼接正确，结果落库"""
        mock_provider.register_stream(
            "hello",
            [StreamChunk(content="Hel"), StreamChunk(content="lo"), StreamChunk(content="!")],
        )
        # 先添加一个 user 消息使得 get_history 有内容
        assistant_manager.history_manager.add_user_prompt("hello", "", OWNER)

        result = _consume(assistant_manager.generate(OWNER))

        assert result == "Hello!"
        # 验证 assistant 消息落库
        msgs = _db_msgs(assistant_manager, OWNER)
        assistant_msgs = [m for m in msgs if m.role == AssistantType.Assistant]
        assert len(assistant_msgs) == 1
        assert assistant_msgs[0].content == "Hello!"

    def test_empty_history(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """空历史（仅有 system prompt）时仍能正常生成"""
        mock_provider.register_stream("mock default", [StreamChunk(content="OK")])
        # 不添加任何 user 消息，get_history 只有 system prompt
        # 由于 mock 按 user content 匹配不到最后一个 user 消息（不存在），走默认响应

        result = _consume(assistant_manager.generate(OWNER))

        # 默认 mock 响应包含 "mock default"
        assert "mock default" in result
        # 仍然落库
        assert _db_msg_count(assistant_manager, OWNER) >= 1

    def test_result_persisted_in_finally(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """验证 generate 结果通过 finally 块落库"""
        mock_provider.register_stream("ping", [StreamChunk(content="pong")])
        assistant_manager.history_manager.add_user_prompt("ping", "", OWNER)

        _consume(assistant_manager.generate(OWNER))

        msgs = _db_msgs(assistant_manager, OWNER)
        contents = [m.content for m in msgs if m.role == AssistantType.Assistant]
        assert "pong" in contents


# ===================================================================
# chat
# ===================================================================


class TestChat:
    def test_basic(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """基本对话：user 和 assistant 消息均落库"""
        mock_provider.register_stream("你好", [StreamChunk(content="你好呀！")])

        result = _consume(assistant_manager.chat("你好", OWNER))

        assert result == "你好呀！"
        msgs = _db_msgs(assistant_manager, OWNER)
        assert len(msgs) == 2  # user + assistant
        assert msgs[0].role == AssistantType.User
        assert msgs[0].content == "你好"
        assert msgs[1].role == AssistantType.Assistant
        assert msgs[1].content == "你好呀！"

    def test_multi_turn(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """多轮对话：历史消息按序保存"""
        mock_provider.register_stream("A", [StreamChunk(content="ReplyA")])
        mock_provider.register_stream("B", [StreamChunk(content="ReplyB")])

        _consume(assistant_manager.chat("A", OWNER))
        _consume(assistant_manager.chat("B", OWNER))

        msgs = _db_msgs(assistant_manager, OWNER)
        assert len(msgs) == 4  # user→assistant→user→assistant
        assert msgs[0].role == AssistantType.User and msgs[0].content == "A"
        assert msgs[1].role == AssistantType.Assistant and msgs[1].content == "ReplyA"
        assert msgs[2].role == AssistantType.User and msgs[2].content == "B"
        assert msgs[3].role == AssistantType.Assistant and msgs[3].content == "ReplyB"

    def test_custom_inject_content(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """自定义 inject_content 被保存到 user 消息中"""
        mock_provider.register_stream("hi", [StreamChunk(content="hello")])

        _consume(assistant_manager.chat("hi", OWNER, inject_content="自定义注入"))

        msgs = _db_msgs(assistant_manager, OWNER)
        user_msg = [m for m in msgs if m.role == AssistantType.User][0]
        assert "自定义注入" in user_msg.system_inject_content

    def test_auto_continue_triggered(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """auto_continue 开启且回复过短时，触发续写循环并 merge"""
        # 设置阈值为 50 字符，mock 返回的首次回复仅 2 字符 → 触发续写
        assistant_manager.history_manager.set_auto_continue(50, OWNER)

        # 首次回复很短（2 字符）
        mock_provider.register_stream("问题", [StreamChunk(content="AB")])
        # 续写轮次：匹配 ContinueWritingPrompt 中的子串 "继续输出后续内容"
        mock_provider.register_stream("继续输出后续内容", [StreamChunk(content="CDEFGHIJ" * 6)])  # 48 字符

        result = _consume(assistant_manager.chat("问题", OWNER))

        # merge 后 content = "AB" + "CDEFGHIJ"*6 = 50 字符，满足阈值
        assert len(result) >= 50
        assert result.startswith("AB")
        assert "CDEFGHIJ" in result

        # DB 中应只有 2 条（user + merged assistant），
        # 因为 auto_continue 中间消息已被 merge_assistant_msg 清理
        msgs = _db_msgs(assistant_manager, OWNER)
        user_msgs = [m for m in msgs if m.role == AssistantType.User]
        assert len(user_msgs) == 1
        assert user_msgs[0].content == "问题"

    def test_auto_continue_multi_loop(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """auto_continue 多轮循环：每轮回复都短于阈值，直到累计足够长"""
        assistant_manager.history_manager.set_auto_continue(30, OWNER)

        # 每轮只返回 5 字符，远低于 30 阈值
        mock_provider.register_stream("反复", [StreamChunk(content="aaaaa")])
        # 续写轮也返回短内容（走默认的短回复）
        mock_provider.register_stream("继续输出后续内容", [StreamChunk(content="bbbbb")])

        result = _consume(assistant_manager.chat("反复", OWNER))

        # 多轮 merge 后最终长度 >= 30（5+5+5+5...至少 6 轮）
        assert len(result) >= 30
        # DB 中应只有 user + merged assistant
        assert _db_msg_count(assistant_manager, OWNER) == 2

    def test_auto_continue_disabled_by_default(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """默认 auto_continue=0，不触发续写循环"""
        mock_provider.register_stream("hi", [StreamChunk(content="Hi")])

        _consume(assistant_manager.chat("hi", OWNER))

        # 只有 user + assistant，没有额外的续写消息
        assert _db_msg_count(assistant_manager, OWNER) == 2


# ===================================================================
# remake
# ===================================================================


class TestRemake:
    def test_basic(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """chat 后 remake：删除旧回复，用原 prompt 重新生成"""
        # 第一轮 chat
        mock_provider.register_stream("原始问题", [StreamChunk(content="旧回答")])
        _consume(assistant_manager.chat("原始问题", OWNER))

        # 注册新回答（同一 prompt）
        mock_provider.register_stream("原始问题", [StreamChunk(content="新回答")])

        result = _consume(assistant_manager.remake(OWNER))

        assert result == "新回答"
        msgs = _db_msgs(assistant_manager, OWNER)
        # 只有 user("原始问题") + assistant("新回答")
        assert len(msgs) == 2
        assert msgs[0].content == "原始问题"
        assert msgs[1].content == "新回答"

    def test_no_history_raises(self, assistant_manager: AssistantManager) -> None:
        """无历史记录时 remake 抛出 LLMIllegalStatusException"""
        with pytest.raises(LLMIllegalStatusException):
            _consume(assistant_manager.remake(OWNER))

    def test_preserves_original_prompt(self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider) -> None:
        """remake 重新生成时使用与原 chat 相同的 prompt"""
        mock_provider.register_stream("保留这个提示词", [StreamChunk(content="回复1")])
        _consume(assistant_manager.chat("保留这个提示词", OWNER))

        mock_provider.register_stream("保留这个提示词", [StreamChunk(content="回复2")])
        _consume(assistant_manager.remake(OWNER))

        msgs = _db_msgs(assistant_manager, OWNER)
        user_msgs = [m for m in msgs if m.role == AssistantType.User]
        assert len(user_msgs) == 1
        assert user_msgs[0].content == "保留这个提示词"

    def test_after_tool_call_remake_succeeds(
        self, assistant_manager: AssistantManager, mock_provider: MockLLMProvider
    ) -> None:
        """工具调用后 remake：remove_last_assistant 正确删除整个工具调用块

        模拟 DB 中的消息序列：
            user: "北京天气怎么样"
            assistant: (tool_calls, content="")   ← 属于助手回复
            tool: (call_1 结果)                    ← 属于助手回复
            assistant: "北京今天晴天"               ← 属于助手回复

        remove_last_assistant 应扫描删除全部 3 条非 user 消息，
        remove_last_user 找到 user 消息并删除，remake 正常执行。
        """
        am = assistant_manager
        am.history_manager.add_user_prompt("北京天气怎么样", "", OWNER)
        am.history_manager.add_assistant_answer(
            "",
            OWNER,
            tool_call_list_json='[{"id":"call_1","type":"function","function":{"name":"weather","arguments":"{}"}}]',  # pyright: ignore[reportArgumentType]
        )
        am.history_manager.add_tool_call_msg("call_1", "晴天, 25°C", owner=OWNER)
        am.history_manager.add_assistant_answer("北京今天晴天", OWNER)

        # 注册 remake 后 chat 所需的流式响应
        mock_provider.register_stream("北京天气怎么样", [StreamChunk(content="新回复：北京晴天")])

        result = _consume(am.remake(OWNER))

        assert result == "新回复：北京晴天"
        # DB 中应只有 2 条：user + 新 assistant
        msgs = _db_msgs(am, OWNER)
        assert len(msgs) == 2
        assert msgs[0].role == AssistantType.User
        assert msgs[0].content == "北京天气怎么样"
        assert msgs[1].role == AssistantType.Assistant
        assert msgs[1].content == "新回复：北京晴天"

    def test_remove_last_assistant_merges_tool_content(
        self, assistant_manager: AssistantManager
    ) -> None:
        """remove_last_assistant 将工具调用块的多条消息内容合并返回"""
        am = assistant_manager
        am.history_manager.add_user_prompt("查询", "", OWNER)
        am.history_manager.add_assistant_answer("让我查一下", OWNER)
        am.history_manager.add_tool_call_msg("call_x", "结果数据", owner=OWNER)
        am.history_manager.add_assistant_answer("查到了：结果数据", OWNER)

        merged = am.history_manager.remove_last_assistant(OWNER)

        assert merged is not None
        # 内容按时间顺序拼接：早 → 晚
        assert merged.content == "让我查一下结果数据查到了：结果数据"
        assert merged.role == AssistantType.Assistant
