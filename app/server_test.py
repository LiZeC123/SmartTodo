from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from entity import Base
from server import *

engine = create_engine('sqlite://', echo=True, future=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(engine)
manager = Manager(db_session)

