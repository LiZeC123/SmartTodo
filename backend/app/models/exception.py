class BaseSmartTodoException(Exception):
    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return self.msg


class UnauthorizedException(BaseSmartTodoException): ...


class UnmatchedException(BaseSmartTodoException): ...


class NotUniqueItemException(BaseSmartTodoException): ...


class IllegalArgumentException(BaseSmartTodoException): ...


class LLMBaseException(BaseSmartTodoException): ...


class LLMIllegalStatusException(LLMBaseException): ...
