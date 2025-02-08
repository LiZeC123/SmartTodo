from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

class Note(Base):
    """便签数据表: 存储创建的便签文本"""
    __tablename__ = "note"

    id: Mapped[int]         = mapped_column(Integer, primary_key=True)
    content: Mapped[str]    = mapped_column(Text, nullable=False)
    owner: Mapped[str]      = mapped_column(String(15), nullable=False)