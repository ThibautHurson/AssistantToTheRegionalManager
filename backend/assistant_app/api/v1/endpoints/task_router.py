from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from backend.assistant_app.models.task_manager import TaskManager, get_task_manager

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

    class Config:
        from_attributes = True

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    task_manager: TaskManager = Depends(get_task_manager)
):
    return task_manager.add_task(
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        priority=task.priority
    )

@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = None,
    priority: Optional[int] = None,
    task_manager: TaskManager = Depends(get_task_manager)
):
    return task_manager.get_tasks(status=status, priority=priority)

@router.get("/tasks/next", response_model=Optional[TaskResponse])
async def get_next_task(
    task_manager: TaskManager = Depends(get_task_manager)
):
    return task_manager.get_next_task()

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task: TaskUpdate,
    task_manager: TaskManager = Depends(get_task_manager)
):
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
    task_manager: TaskManager = Depends(get_task_manager)
):
    if not task_manager.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success"} 