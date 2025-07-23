from sqlalchemy import Column, String, Integer, DateTime, Text, func
from backend.assistant_app.api_integration.db import Base, get_db

class TicketCounter(Base):
    __tablename__ = "ticket_counter"

    id = Column(Integer, primary_key=True)
    last_number = Column(Integer, default=0)

def generate_ticket_id():
    db = next(get_db())
    try:
        counter = db.query(TicketCounter).first()
        if not counter:
            counter = TicketCounter(last_number=0)
            db.add(counter)

        counter.last_number += 1
        db.commit()
        return f"ATTRM-{counter.last_number:06d}"  # Pad with zeros to 6 digits
    finally:
        db.close()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    ticket_id = Column(String, unique=True, index=True, default=generate_ticket_id)
    title = Column(String, nullable=False)
    description = Column(Text)
    due_date = Column(DateTime(timezone=True))
    priority = Column(Integer, default=1)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(String, nullable=False, index=True)
    gmail_message_id = Column(String, unique=True, nullable=True, index=True)