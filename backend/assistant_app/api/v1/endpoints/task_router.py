from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from backend.assistant_app.models.task_manager import TaskManager
from backend.assistant_app.services.auth_service import auth_service

router = APIRouter()

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: int = 1

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[int] = None
    status: Optional[str] = None

class TaskResponse(TaskBase):
    id: str
    ticket_id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    user_id: str
    gmail_message_id: Optional[str] = None
    gmail_link: Optional[str] = None

    class Config:
        from_attributes = True

def get_task_manager(session_id: str = Query(..., description="Session ID for authentication")) -> TaskManager:
    """Get task manager for authenticated user."""
    user = auth_service.validate_session(session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return TaskManager(user.email)

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    session_id: str = Query(..., description="Session ID for authentication")
):
    task_manager = get_task_manager(session_id)
    return task_manager.add_task(
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        priority=task.priority
    )

@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    session_id: str = Query(..., description="Session ID for authentication"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[int] = Query(None, description="Filter by priority")
):
    task_manager = get_task_manager(session_id)
    return task_manager.get_tasks(status=status, priority=priority)

@router.get("/tasks/next", response_model=Optional[TaskResponse])
async def get_next_task(session_id: str = Query(..., description="Session ID for authentication")):
    task_manager = get_task_manager(session_id)
    return task_manager.get_next_task()

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task: TaskUpdate,
    session_id: str = Query(..., description="Session ID for authentication")
):
    task_manager = get_task_manager(session_id)
    updated_task = task_manager.update_task(
        task_id=task_id,
        **task.model_dump(exclude_unset=True)
    )
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated_task

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    session_id: str = Query(..., description="Session ID for authentication")
):
    task_manager = get_task_manager(session_id)
    if not task_manager.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success"}