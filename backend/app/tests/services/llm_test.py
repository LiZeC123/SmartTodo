from typing import Any, Generator, List

from app.services.config_manager import ConfigManager
from app.services.item_manager import ItemManager
from app.services.llm_manager import AssistantManager
from app.services.tomato_manager import TomatoManager, TomatoRecordManager
from app.tests.services.make_db import make_new_db
from app.tools.llm import LLMClient

from openai.types.chat import ChatCompletionMessageParam


MockResponse = "MockLLMClient Response"


class MockLLMClient(LLMClient):
    def __init__(self, config_manager: ConfigManager) -> None:
        super().__init__(config_manager)

    def generate_stream(
        self, history: List[ChatCompletionMessageParam]
    ) -> Generator[str, Any, None]:
        yield MockResponse


db = make_new_db()
config_manager = ConfigManager()
llm_manager = MockLLMClient(config_manager)
item_manager = ItemManager(db)
tomato_manager = TomatoManager(db, item_manager)
tomato_record_manager = TomatoRecordManager(db, item_manager)


assistant_manager = AssistantManager(
    llm_manager, item_manager, tomato_manager, tomato_record_manager
)
owner = "user"


def finish(g: Generator[str, Any, None]):
    [_ for _ in g]


# 先完成基础测试, llm功能不稳定, 单元测试写太多, 以后可能都是负资产
def test_base():
    g = assistant_manager.chat("早上好", owner=owner)
    finish(g)
    memory = assistant_manager.get_memory(owner)
    assert len(memory.messages) == 3
    assert memory.messages[2].message.get("content") == MockResponse

    d = assistant_manager.get_web_history(owner)
    assert len(d) == 2  # 只展示用户输入和模型输出, sp自动隐藏

    g = assistant_manager.remake(owner=owner)
    finish(g)
    assert len(memory.messages) == 3

    g = assistant_manager.replace("晚上好", owner=owner)
    finish(g)
    assert len(memory.messages) == 3

    assert assistant_manager.delete(owner=owner)
    assert len(memory.messages) == 1

    assert assistant_manager.delete(owner=owner)
    assert len(memory.messages) == 1

    assert assistant_manager.reset(owner=owner)
    assert len(memory.messages) == 1

    g = assistant_manager.dump_history(owner)
    finish(g)  # 访问一次memory, 触发sp构造

    # 至少有sp才能再次重置
    assert assistant_manager.reset(owner=owner)
    assert len(memory.messages) == 1
