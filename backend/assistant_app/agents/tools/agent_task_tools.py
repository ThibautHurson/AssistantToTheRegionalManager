from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from backend.assistant_app.models.task_manager import TaskManager

class TaskInput(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: int = 1
    status: str = "pending"


def add_task(user_email: str, title: str, description: Optional[str] = None, 
             due_date: Optional[datetime] = None, priority: int = 1) -> str:
    """Add a new task to the task manager.
    
    Args:
        user_email: The user's email address
        title: The title of the task
        description: Optional description of the task
        due_date: Optional due date for the task
        priority: Task priority (1-5, default 1)
    
    Returns:
        str: A message indicating the task was added successfully
    """
    task_manager = TaskManager(user_email)
    task = task_manager.add_task(
        title=title,
        description=description,
        due_date=due_date,
        priority=priority
    )
    return f"Task '{task.title}' added successfully with ID: {task.id}"


def delete_task(user_email: str, task_id: str) -> str:
    """Delete a task from the task manager.
    
    Args:
        user_email: The user's email address
        task_id: The ID of the task to delete
    
    Returns:
        str: A message indicating the task was deleted successfully
    """
    task_manager = TaskManager(user_email)
    if task_manager.delete_task(task_id):
        return f"Task {task_id} deleted successfully"
    return f"Task {task_id} not found"


def update_task(user_email: str, task_id: str, **kwargs) -> str:
    """Update a task in the task manager.
    
    Args:
        user_email: The user's email address
        task_id: The ID of the task to update
        **kwargs: Fields to update (title, description, due_date, priority, status)
    
    Returns:
        str: A message indicating the task was updated successfully
    """
    task_manager = TaskManager(user_email)
    updated_task = task_manager.update_task(task_id, **kwargs)
    if updated_task:
        return f"Task '{updated_task.title}' updated successfully"
    return f"Task {task_id} not found"


def list_tasks(user_email: str, status: Optional[str] = None, priority: Optional[int] = None) -> str:
    """List all tasks for the user.
    
    Args:
        user_email: The user's email address
        status: Optional status filter
        priority: Optional priority filter (1-5)
    
    Returns:
        str: A formatted list of tasks
    """
    task_manager = TaskManager(user_email)
    tasks = task_manager.get_tasks(status=status, priority=priority)
    
    if not tasks:
        return "No tasks found"
    
    result = "Tasks:\n"
    for task in tasks:
        result += f"\n- {task.title} (ID: {task.id})"
        if task.description:
            result += f"\n  Description: {task.description}"
        if task.due_date:
            result += f"\n  Due: {task.due_date}"
        result += f"\n  Priority: {task.priority}"
        result += f"\n  Status: {task.status}\n"
    
    return result


def get_next_task(user_email: str) -> str:
    """Get the next task based on priority and due date.
    
    Args:
        user_email: The user's email address
    
    Returns:
        str: Information about the next task
    """
    task_manager = TaskManager(user_email)
    next_task = task_manager.get_next_task()
    
    if not next_task:
        return "No pending tasks found"
    
    result = f"Next task: {next_task.title} (ID: {next_task.id})"
    if next_task.description:
        result += f"\nDescription: {next_task.description}"
    if next_task.due_date:
        result += f"\nDue: {next_task.due_date}"
    result += f"\nPriority: {next_task.priority}"
    result += f"\nStatus: {next_task.status}"
    
    return result 