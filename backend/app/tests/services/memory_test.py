from app.models.memory import KB, MemoryPolicy
from app.services.assistant_history import AssistantHistoryManager
from app.services.assistant_memory import AssistantMemoryManager
from app.services.config_manager import ConfigManager
from app.services.role_manager import RoleManager
from app.tests.services.make_db import make_new_db
from app.tools.llm import LLMClient

all_memory_policy = MemoryPolicy(
    enable_role_setting=True, enable_preference=True, max_topic_num=5, max_diary_num=5, raw_content_size=5 * KB
)


class MockRoleManager(RoleManager):
    pass


owner = "user"
db = make_new_db()
mock_role_manager = MockRoleManager()
llm_client = LLMClient(ConfigManager())
hm = AssistantHistoryManager(db)
memory_manager = AssistantMemoryManager(mock_role_manager, llm_client, hm)
