import json
from collections.abc import Callable, Sequence

from openai.types.chat import (
    ChatCompletionToolUnionParam,
)
from openai.types.chat.chat_completion_function_tool_param import ChatCompletionFunctionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition

from app.models.exception import LLMIllegalStatusException
from app.models.item import Item
from app.services.assistant import AssistantManager
from app.tools.log import logger
from app.tools.time import get_datetime_from_str


def with_metadata(struct: ChatCompletionFunctionToolParam):
    """装饰器：自动获取函数名并关联自定义结构体"""

    def decorator(func):
        # 自动获得函数名字符串
        func._func_name = func.__name__
        # 自动填充需要保持一致的字段
        struct["function"]["name"] = func.__name__
        # 关联自定义结构体变量
        func._struct = struct
        return func  # 原样返回，不改变函数本身

    return decorator


# 从实际效果来看, 在工具中说明格式比在SP中说明格式效果更稳定
CreatItemTool = ChatCompletionFunctionToolParam(
    type="function",
    function=FunctionDefinition(
        name="{}",
        description="为用户创建一个待办事项",
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "待办事项的名称, 格式为[助手名称]:[事项主题]",
                },
                "deadline": {
                    "type": "string",
                    "format": "date-time",
                    "description": "截止时间, 格式为2006-01-02 15:04:05",
                },
                "expected_tomato": {
                    "type": "integer",
                    "description": "该待办事项预期需要的番茄钟数量, 取值范围为闭区间[1, 4]",
                    "default": 1,
                },
                "priority": {
                    "type": "string",
                    "description": "优先级，常用取值：'p0'(两天内完成)、'p1'(本周末前完成)、'p2'(下周末前完成)",
                    "default": "p1",
                    "enum": ["p0", "p1", "p2"],
                },
            },
            "required": ["name", "deadline", "expected_tomato", "priority"],
        },
    ),
)

SupportQueryTyep = ["今日待办", "已逾期任务"]
QueryTodoSystemTool = ChatCompletionFunctionToolParam(
    type="function",
    function=FunctionDefinition(
        name="{}",
        description="查询用户待办事项系统的数据. 指定一个查询的类别, 按照分组的形式返回相关数据的明细.",
        parameters={
            "type": "object",
            "properties": {
                "query_type": {"type": "string", "description": "要查询的数据的类别", "enum": SupportQueryTyep},
            },
            "required": ['query_type'],
        },
    ),
)


class AssistantTool:
    def __init__(self, m: AssistantManager, owner: str) -> None:
        self.item_manager = m.item_manager
        self.role_manager = m.role_manager
        self.llm_manager = m.llm_manager
        self.owner = owner

    def collect(self) -> tuple[Sequence[ChatCompletionToolUnionParam], dict[str, Callable[[str], str]]]:
        metadata_list = []
        method_dict = {}

        # 按类定义顺序扫描类属性（Python 3.7+ 保留插入顺序）
        for name, attr in self.__class__.__dict__.items():
            if hasattr(attr, "_func_name") and hasattr(attr, "_struct"):
                func_name = attr._func_name
                struct = attr._struct
                metadata_list.append(struct)
                # 绑定到 self 的方法实例
                method_dict[func_name] = getattr(self, name)

        return metadata_list, method_dict

    @with_metadata(CreatItemTool)
    def create_item(self, arg_json: str) -> str:
        try:
            args: dict[str, str] = json.loads(arg_json)
            item = Item(
                name=args.get("name"),
                item_type="single",
                owner=self.owner,
                deadline=get_datetime_from_str(args.get("deadline", "")),
                priority=args.get("priority"),
            )
            self.item_manager.create(item)
            self.item_manager.db.commit()
        except Exception as e:
            logger.exception(e)
            return f"error: {e}"
        return "success"

    @with_metadata(QueryTodoSystemTool)
    def query_todo_system(self, arg_json: str) -> str:
        args: dict[str, str] = json.loads(arg_json)
        query_type = args.get("query_type")
        if query_type not in SupportQueryTyep:
            return f"未知的查询类型: {query_type}"

        try:
            if query_type == "今日待办":
                groups = self.item_manager.get_item_with_sub_task(owner=self.owner)
                return self.format_group(groups)
            if query_type == "已逾期任务":
                groups = self.item_manager.get_deadline_item(self.owner)
                return self.format_group(groups)

            # 不应该存在这种情况, 如果确实出现了, 那么就先手动抛出异常, 然后在下面被捕获
            raise LLMIllegalStatusException(f"{query_type} 已经注册但未提供逻辑支持")
        except Exception as e:
            logger.exception(e)
            return f"error: {e}"

    @staticmethod
    def format_group(groups) -> str:
        if not groups:
            return ""
        lines = []
        idx = 1
        for group in groups:
            parent = group.get("self", {})
            children = group.get("children", [])
            group_name = parent.get("name", "全局任务")
            lines.append(f"【分组: {group_name}】")
            for d in children:
                name = d.get("name", "(无名称)")
                deadline = d.get("deadline", "(无截止时间)")
                priority = d.get("priority", "(无优先级)")
                deadline = deadline if deadline else "(无截止时间)"
                priority = priority if priority else "(无优先级)"
                lines.append(f"  {idx}. {name}")
                lines.append(f"     截止时间: {deadline}")
                lines.append(f"     优先级: {priority}")

                expected_tomato = d.get("expected_tomato")
                used_tomato = d.get("used_tomato")

                if expected_tomato == used_tomato:
                    lines.append("     任务状态: 已完成")
                else:
                    lines.append(f"     任务状态: 剩余{expected_tomato - used_tomato}个番茄钟")

                idx += 1
            lines.append("")
        return "\n".join(lines)
