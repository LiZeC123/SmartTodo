# 创建待办事项工具
from openai.types.chat.chat_completion_function_tool_param import ChatCompletionFunctionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition


CreatItemTool: ChatCompletionFunctionToolParam = ChatCompletionFunctionToolParam(
    type="function",
    function=FunctionDefinition(
        name="create_item",
        description="创建一个新的待办事项",
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "待办事项的名称",
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