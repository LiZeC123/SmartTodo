import os
import re

from mapper import MemoryDataBase
from service4file import FileManager
from tool4log import logger
from tool4time import parse_deadline_str, get_datetime_from_str

op_pattern = re.compile(r"->|=")
name_pattern = re.compile(r"<(\w+)>")
date_pattern = re.compile(r"(\d+)[.](\d+)(:\d+)?$")  # => 6.18:12 => 6月18日12点

literal_map = {
    "none": None,
    "true": True,
    "True": True,
    "false": False,
    "False": False
}

attr_name_map = {
    "id": "id",
    "name": "name",
    "u": "urgent",
    "dl": "deadline",
    "old": "old",
    "re": "repeatable",
    "sp": "specific",
    "wk": "work",
    "url": "url",
    "p": "parent"
}


def value_check(name, value):
    if value is None:
        return True
    if name in ["id", "urgent", "specific", "parent"]:
        if not str(value).isnumeric():
            logger.error(f"ErrorType: Attribute {name} except Integer Type But Get Value {value}")
            return False
    if name in ["deadline"]:
        try:
            get_datetime_from_str(value)
        except ValueError or TypeError:
            logger.error(f"ErrorType: Attribute {name} except Date Type But Get Value {value}")
            return False
    if name in ["old", "repeatable", "work"]:
        if str(value) != "True" and str(value) != "False":
            logger.error(f"ErrorType: Attribute {name} except Boolean Type But Get Value {value}")
            return False
    return True


def grammar_checked(parts):
    if len(parts) < 2:
        logger.error(f"Grammar Check: Function Name Not Found. Got {parts}")
        return False
    return True


class OpInterpreter:
    def __init__(self, mapper: MemoryDataBase, file_manager: FileManager):
        self.mapper: MemoryDataBase = mapper
        self.fileManager: FileManager = file_manager

    def exec_cmd(self, code: str):
        if code.startswith("set"):
            return self.exec_set(code)
        elif code.startswith("fun"):
            return self.exec_fun(code)
        else:
            logger.error("Unknown Command")

    def exec_set(self, code: str):
        try:
            logger.info(f"OpInterpreter: Input Code --> {code}")
            names, attrs, values = re.split(op_pattern, code)
            names = names.split(",")
            attrs = attrs.split(",")
            values = values.split(",")
            ids = self.get_id_by_name(names)
            attrs = self.get_full_attr_name(attrs)
            values = self.get_value_real_value(values)
            logger.info(f"OpInterpreter: Analysis Result: ids --> {ids}  attrs --> {attrs} values --> {values}")
            for iid in ids:
                if iid is not None:
                    for attr, value in zip(attrs, values):
                        if value_check(attr, value):
                            self.mapper.exec_set_cmd(iid, attr, value)

        except ValueError:
            logger.exception(f"OpInterpreter: Bad Code --> {code}")

    def exec_fun(self, code: str):
        try:
            logger.info(f"OpInterpreter: Input Code --> {code}")
            part = code.split()
            if grammar_checked(part):
                func_name = part[1]
                if func_name == "public":
                    return self.file2public(*part[2:])
                elif func_name == 'private':
                    return self.file2private(*part[2:])

        except ValueError:
            logger.exception(f"OpInterpreter: Bad Code --> {code}")

    def get_id_by_name(self, names):
        ids = []
        for name in names:
            ids.append(self.mapper.get_id_by_name(name.strip()))
        return ids

    @staticmethod
    def get_full_attr_name(attrs):
        full = []
        for attr in attrs:
            name = attr.strip()
            if name in attr_name_map:
                full.append(attr_name_map[name])
        return full

    def get_value_real_value(self, values):
        real = []
        for value in values:
            value = value.strip()
            match_name = name_pattern.match(value)
            match_date = date_pattern.match(value)
            if match_name:
                var_name = match_name.groups()
                # get_id_by_name始终返回列表, 所以只选择第一个元素
                real.append(self.get_id_by_name(var_name)[0])
            elif match_date:
                real.append(parse_deadline_str(value))
            elif value in literal_map:
                real.append(literal_map.get(value))
            elif value.isdigit():
                real.append(int(value))
            else:
                real.append(value)
        return real

    def file2public(self, args):
        ids = self.get_id_by_name(args.split(","))
        for iid in ids:
            with self.mapper.select(iid) as item:
                src = item['url']
                _, filename = os.path.split(src)
                self.fileManager.file2public(filename)
                self.fileManager.remove(filename, filetype='private')
                item['url'] = self.fileManager.get_file_url(filename, filetype='public')

    def file2private(self, args):
        ids = self.get_id_by_name(args.split(","))
        for iid in ids:
            with self.mapper.select(iid) as item:
                src = item['url']
                _, filename = os.path.split(src)
                self.fileManager.file2private(filename)
                self.fileManager.remove(filename, filetype='public')
                item['url'] = self.fileManager.get_file_url(filename, filetype='private')
