
import sqlalchemy as sal

from entity import Summary
from tool4time import today_str


class ReportManager:
    def __init__(self, db) -> None:
        self.db = db

    def update_summary(self, content:str, owner: str)-> bool:
        day = today_str()
        stmt = sal.select(Summary).where(Summary.create_time == day)
        summary = self.db.scalar(stmt)
        if summary is None:
            summary = Summary(create_time=day, content=content, owner=owner)
        else:
            summary.content = content
        self.db.add(summary)
        self.db.commit()
        return True

    def get_today_summary(self, owner: str)-> str:
        day = today_str()
        stmt = sal.select(Summary.content).where(Summary.create_time == day, owner=owner)
        content =  self.db.scalar(stmt)
        if content is None:
            return ""
        return content

