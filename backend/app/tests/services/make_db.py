from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from app.models.base import Base

def make_new_db():
    engine = create_engine(url='sqlite://', echo=True, future=True)
    Base.metadata.create_all(engine)
    return scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))