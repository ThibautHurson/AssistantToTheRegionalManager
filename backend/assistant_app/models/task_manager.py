from typing import List, Optional
from datetime import datetime
from sqlalchemy import desc
import uuid
from fastapi import Query

from backend.assistant_app.models.task import Task as TaskModel
from backend.assistant_app.api_integration.db import get_db

class Task:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.ticket_id = kwargs.get('ticket_id')
        self.title = kwargs.get('title')
        self.description = kwargs.get('description')
        self.due_date = kwargs.get('due_date')
        self.priority = kwargs.get('priority', 1)
        self.status = kwargs.get('status', 'pending')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.user_id = kwargs.get('user_id')
        self.gmail_message_id = kwargs.get('gmail_message_id')

    @property
    def gmail_link(self):
        if self.gmail_message_id:
            return f"https://mail.google.com/mail/u/0/#inbox/{self.gmail_message_id}"
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id,
            'gmail_message_id': self.gmail_message_id,
            'gmail_link': self.gmail_link
        }

class TaskManager:
    def __init__(self, user_email: str):
        self.user_email = user_email  # Using user email as user_id

    def add_task(self, title: str, description: Optional[str] = None,
                 due_date: Optional[datetime] = None, priority: int = 1, msg_id: str = None) -> Task:
        db = next(get_db())
        try:
            task = TaskModel(
                id=str(uuid.uuid4()),
                gmail_message_id=msg_id,
                title=title,
                description=description,
                due_date=due_date,
                priority=priority,
                user_id=self.user_email
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return Task(**task.__dict__)
        finally:
            db.close()

    def get_tasks(self, status: Optional[str] = None, priority: Optional[int] = None) -> List[Task]:
        db = next(get_db())
        try:
            query = db.query(TaskModel).filter(TaskModel.user_id == self.user_email)

            if status:
                query = query.filter(TaskModel.status == status)
            if priority is not None:
                query = query.filter(TaskModel.priority == priority)

            # Order by priority (high to low) and then by due date
            query = query.order_by(desc(TaskModel.priority), TaskModel.due_date)

            tasks = query.all()
            return [Task(**task.__dict__) for task in tasks]
        finally:
            db.close()

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        db = next(get_db())
        try:
            task = db.query(TaskModel).filter(
                TaskModel.id == task_id,
                TaskModel.user_id == self.user_email
            ).first()

            if not task:
                return None

            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            db.commit()
            db.refresh(task)
            return Task(**task.__dict__)
        finally:
            db.close()

    def delete_task(self, task_id: str) -> bool:
        db = next(get_db())
        try:
            result = db.query(TaskModel).filter(
                TaskModel.id == task_id,
                TaskModel.user_id == self.user_email
            ).delete()
            db.commit()
            return result > 0
        finally:
            db.close()

    def get_next_task(self) -> Optional[Task]:
        """Get the next task based on priority and due date"""
        db = next(get_db())
        try:
            task = db.query(TaskModel)\
                .filter(
                    TaskModel.user_id == self.user_email,
                    TaskModel.status == 'pending'
                )\
                .order_by(desc(TaskModel.priority))\
                .order_by(TaskModel.due_date)\
                .first()

            if task:
                return Task(**task.__dict__)
            return None
        finally:
            db.close()

def get_task_manager(session_id: str = Query(..., description="Session ID")) -> TaskManager:
    """Get or create a task manager for a user"""
    return TaskManager(session_id)