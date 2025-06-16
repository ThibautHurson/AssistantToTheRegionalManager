from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from backend.assistant_app.api_integration.db import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    due_date = Column(DateTime(timezone=True))
    priority = Column(Integer, default=1)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(String, nullable=False, index=True) 