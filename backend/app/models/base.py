from datetime import datetime

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    def to_dict(self):
        d = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name, None)
            if type(v) is datetime:
                d[c.name] = v.strftime("%Y-%m-%d %H:%M:%S")
            else:
                d[c.name] = v
        return d
