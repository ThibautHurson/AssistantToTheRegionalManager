from typing import Dict, Any
from backend.assistant_app.models.task_manager import TaskManager
from backend.assistant_app.memory.context_manager import HybridContextManager

class UserDataService:
    """Service for managing user data deletion for privacy compliance."""
    
    def __init__(self):
        pass

    def clear_user_data(self, user_email: str) -> Dict[str, Any]:
        """
        Clear all data for a specific user including tasks, vector store, and Redis data.
        
        Args:
            user_email: User's email address
            
        Returns:
            Dict containing deletion results
        """
        print(f"Starting comprehensive data deletion for user: {user_email}")
        
        results = {
            "user_id": user_email,
            "vector_store_cleared": False,
            "redis_keys_deleted": 0,
            "database_tasks_deleted": 0,
            "success": True,
            "errors": []
        }
        
        try:

            try:
                # 1. Clear vector store and redis history data
                context_manager = HybridContextManager(
                    user_id=user_email
                )
                clear_memory_data = context_manager.clear_user_data()

                results["vector_store_cleared"] = clear_memory_data["vector_store_cleared"]
                results["redis_keys_deleted"] = clear_memory_data["redis_keys_deleted"]
            except Exception as e:
                error_msg = f"Error clearing vector store: {e}"
                print(error_msg)
                results["errors"].append(error_msg)
            
            # 3. Clear database tasks
            try:
                task_manager = TaskManager(user_email)
                all_tasks = task_manager.get_tasks()
                deleted_count = 0
                
                for task in all_tasks:
                    try:
                        if task_manager.delete_task(task.id):
                            deleted_count += 1
                        else:
                            print(f"Warning: Could not delete task {task.id}")
                    except Exception as e:
                        print(f"Error deleting task {task.id}: {e}")
                
                results["database_tasks_deleted"] = deleted_count
                print(f"✓ Database tasks deleted: {deleted_count} for user {user_email}")
            except Exception as e:
                error_msg = f"Error clearing database tasks: {e}"
                print(error_msg)
                results["errors"].append(error_msg)
            
            print(f"Completed data deletion for user: {user_email}")
            print(f"- Vector store: {'Cleared' if results['vector_store_cleared'] else 'Failed'}")
            print(f"- Redis keys: {results['redis_keys_deleted']} deleted")
            print(f"- Database tasks: {results['database_tasks_deleted']} deleted")
            
            if results["errors"]:
                results["success"] = False
                print(f"Errors encountered: {results['errors']}")
            
        except Exception as e:
            error_msg = f"Unexpected error during data deletion: {e}"
            print(error_msg)
            results["errors"].append(error_msg)
            results["success"] = False
        
        return results 