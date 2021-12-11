from os.path import join

from tool4time import now, now_str, parse_timestamp


class TomatoManager:
    DATABASE_FOLDER = "data/database"
    DATA_FILE = join(DATABASE_FOLDER, "TomatoRecord.dat")

    def __init__(self):
        self.data = {}
        self.taskName = ""
        self.startTime = 0

    def start_task(self, xid: int, name: str, owner: str):
        self.data[owner] = {"id": xid, "name": name, "startTime": now().timestamp()}

    def finish_task(self, xid: int, owner: str):
        if self.check_id(xid, owner):
            self.__insert_record(owner)

    def get_task(self, owner: str):
        if owner not in self.data:
            self.data[owner] = {"id": 0, "name": "当前无任务", "startTime": 0}
        return self.data[owner]

    def check_id(self, xid: int, owner: str):
        if owner in self.data:
            return self.data[owner]['id'] == xid
        else:
            return False

    def clear_task(self, owner: str):
        self.data[owner] = {"id": 0, "name": "当前无任务", "startTime": 0}

    def __insert_record(self, owner: str):
        record = self.data[owner]
        start_time = parse_timestamp(record['startTime'])
        name = record['name']

        with open(TomatoManager.DATA_FILE, "a", encoding="utf-8") as f:
            f.write(f"{start_time} | {now_str()} | {owner} | {name}\n")
