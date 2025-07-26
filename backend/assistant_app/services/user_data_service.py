from typing import Dict, Any
from backend.assistant_app.models.task_manager import TaskManager
from backend.assistant_app.memory.context_manager import HybridContextManager
from backend.assistant_app.utils.logger import user_logger, error_logger


class UserDataService:
    """Service for comprehensive user data management and deletion."""

    def clear_user_data(self, user_email: str) -> Dict[str, Any]:
        """
        Clear all data for a specific user including tasks, vector store, and
        Redis data.

        Args:
            user_email: User's email address
        Returns:
            Dict containing deletion results
        """

        results = {
            "user_id": user_email,
            "vector_store_cleared": False,
            "redis_keys_deleted": 0,
            "database_tasks_deleted": 0,
            "success": True,
            "errors": []
        }

        # 1. Clear vector store data
        try:
            context_manager = HybridContextManager(user_id=user_email)
            vector_results = context_manager.clear_user_data()
            results["vector_store_cleared"] = vector_results["vector_store_cleared"]
            results["redis_keys_deleted"] = vector_results["redis_keys_deleted"]
        except Exception as e:
            error_msg = f"Error clearing vector store for {user_email}: {e}"
            results["errors"].append(error_msg)
            error_logger.log_error(e, {"user_email": user_email, "operation": "vector_store_clear"})

        # 2. Clear database tasks
        try:
            task_manager = TaskManager(user_email)
            all_tasks = task_manager.get_tasks()
            deleted_count = 0
            for task in all_tasks:
                try:
                    if task_manager.delete_task(task.id):
                        deleted_count += 1
                    else:
                        error_logger.log_info(f"Warning: Could not delete task {task.id}", {"user_email": user_email})
                except Exception as e:
                    error_logger.log_error(e, {"user_email": user_email, "operation": "database_tasks_delete", "task_id": task.id})
            results["database_tasks_deleted"] = deleted_count
            user_logger.log_info(f"Database tasks deleted", {
                "user_email": user_email,
                "deleted_count": deleted_count
            })
        except Exception as e:
            error_msg = f"Error deleting database tasks for {user_email}: {e}"
            results["errors"].append(error_msg)
            error_logger.log_error(e, {"user_email": user_email, "operation": "database_tasks_delete"})

        # 3. Final status
        if results["errors"]:
            results["success"] = False
            user_logger.log_warning(f"Completed data deletion for user: {user_email} with errors", {
                "user_email": user_email,
                "errors": results["errors"]
            })
        else:
            user_logger.log_info(f"Completed data deletion for user: {user_email}", {
                "user_email": user_email,
                "vector_store_cleared": results["vector_store_cleared"],
                "redis_keys_deleted": results["redis_keys_deleted"],
                "database_tasks_deleted": results["database_tasks_deleted"]
            })

        return results
