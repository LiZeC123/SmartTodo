# 创建待办事项工具
from openai.types.chat.chat_completion_function_tool_param import ChatCompletionFunctionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition

# 从实际效果来看, 在工具中说明格式比在SP中说明格式效果更稳定
CreatItemTool = ChatCompletionFunctionToolParam(
    type="function",
    function=FunctionDefinition(
        name="create_item",
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
                "priority": {
                    "type": "string",
                    "description": "优先级，常用取值：'p0'(两天内完成)、'p1'(本周末前完成)、'p2'(下周末前完成)",
                    "default": "p1",
                    "enum": ["p0", "p1", "p2"],
                },
            },
            "required": ["name", "deadline", "priority"],
        },
    ),
)

AnyQueryTool = ChatCompletionFunctionToolParam(
    type="function",
    function=FunctionDefinition(
        name="query_info",
        description="向系统查询需要的信息",
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "你的名字, 该字段用于权限检查",
                },
                "question": {
                    "type": "string",
                    "description": "查询的问题, 使用自然语言清晰准确的描述背景和你要问的问题",
                },
            },
            "required": ["name", "question"],
        },
    ),
)

GetDeadlineItemTool = ChatCompletionFunctionToolParam(
    type="function",
    function=FunctionDefinition(
        name="get_deadline_item",
        description="查询当前用户所有已过期的待办事项, 返回每个过期事项的名称、截止时间和优先级",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
)
