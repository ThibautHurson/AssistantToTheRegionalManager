from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
from fastapi import Query

from backend.assistant_app.models.task import Task as TaskModel
from backend.assistant_app.api_integration.db import get_db

class Task:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.title = kwargs.get('title')
        self.description = kwargs.get('description')
        self.due_date = kwargs.get('due_date')
        self.priority = kwargs.get('priority', 1)
        self.status = kwargs.get('status', 'pending')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.user_id = kwargs.get('user_id')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id
        }

class TaskManager:
    def __init__(self, session_id: str):
        self.user_id = session_id  # Using session_id as user_id

    def add_task(self, title: str, description: Optional[str] = None, 
                 due_date: Optional[datetime] = None, priority: int = 1) -> Task:
        db = next(get_db())
        task = TaskModel(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            user_id=self.user_id
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return Task(**task.__dict__)

    def get_tasks(self, status: Optional[str] = None, priority: Optional[int] = None) -> List[Task]:
        db = next(get_db())
        query = db.query(TaskModel).filter(TaskModel.user_id == self.user_id)
        
        if status:
            query = query.filter(TaskModel.status == status)
        if priority is not None:
            query = query.filter(TaskModel.priority == priority)
            
        # Order by priority (high to low) and then by due date
        query = query.order_by(desc(TaskModel.priority), TaskModel.due_date)
        
        tasks = query.all()
        return [Task(**task.__dict__) for task in tasks]

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        db = next(get_db())
        task = db.query(TaskModel).filter(
            TaskModel.id == task_id,
            TaskModel.user_id == self.user_id
        ).first()
        
        if not task:
            return None
            
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        db.commit()
        db.refresh(task)
        return Task(**task.__dict__)

    def delete_task(self, task_id: str) -> bool:
        db = next(get_db())
        result = db.query(TaskModel).filter(
            TaskModel.id == task_id,
            TaskModel.user_id == self.user_id
        ).delete()
        db.commit()
        return result > 0

    def get_next_task(self) -> Optional[Task]:
        """Get the next task based on priority and due date"""
        db = next(get_db())
        task = db.query(TaskModel)\
            .filter(
                TaskModel.user_id == self.user_id,
                TaskModel.status == 'pending'
            )\
            .order_by(desc(TaskModel.priority))\
            .order_by(TaskModel.due_date)\
            .first()
        
        if task:
            return Task(**task.__dict__)
        return None

def get_task_manager(session_id: str = Query(..., description="Session ID")) -> TaskManager:
    """Get or create a task manager for a user"""
    return TaskManager(session_id)