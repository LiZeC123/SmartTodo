class BaseSmartTodoException(Exception):
    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return self.msg


class UnauthorizedException(BaseSmartTodoException):
    ...

class UnmatchedException(BaseException):
    ...


class NotUniqueItemException(BaseSmartTodoException):
    ...


class IllegalArgumentException(BaseSmartTodoException):
    ...
