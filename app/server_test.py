from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Base
from server import *
from tool4log import logger

engine = create_engine('sqlite://', echo=True, future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)
manager = Manager(db_session)


def test_exception():
    try:
        raise UnauthorizedException("msg")
    except UnauthorizedException as e:
        logger.exception(e)


def test_item():
    item = Item(id=1, name="item")
    print(item)