import streamlit as st
import httpx
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
FASTAPI_URI = os.getenv("FASTAPI_URI", "http://localhost:8000")
SESSION_ID = os.getenv("SESSION_ID", "hursonthibaut@gmail.com")

def show_task_manager():
    st.title("Task Manager")
    
    # Add new task
    with st.form("new_task"):
        st.subheader("Add New Task")
        title = st.text_input("Title")
        description = st.text_area("Description")
        due_date = st.date_input("Due Date")
        priority = st.slider("Priority", 1, 5, 1)
        
        if st.form_submit_button("Add Task"):
            if title:
                try:
                    response = httpx.post(
                        f"{FASTAPI_URI}/tasks",
                        json={
                            "title": title,
                            "description": description,
                            "due_date": due_date.isoformat() if due_date else None,
                            "priority": priority
                        },
                        params={"session_id": SESSION_ID},
                        verify=False
                    )
                    response.raise_for_status()
                    st.success("Task added successfully!")
                except Exception as e:
                    st.error(f"Error adding task: {str(e)}")
            else:
                st.error("Title is required!")

    # Get next task
    st.subheader("Next Task")
    try:
        response = httpx.get(
            f"{FASTAPI_URI}/tasks/next",
            params={"session_id": SESSION_ID},
            verify=False
        )
        response.raise_for_status()
        next_task = response.json()
        if next_task:
            st.info(f"Next task: {next_task['title']} (Priority: {next_task['priority']})")
        else:
            st.info("No pending tasks!")
    except Exception as e:
        st.error(f"Error getting next task: {str(e)}")

    # List all tasks
    st.subheader("All Tasks")
    try:
        response = httpx.get(
            f"{FASTAPI_URI}/tasks",
            params={"session_id": SESSION_ID},
            verify=False
        )
        response.raise_for_status()
        tasks = response.json()
        
        for task in tasks:
            with st.expander(f"{task['title']} (Priority: {task['priority']})"):
                st.write(f"Description: {task['description']}")
                if task['due_date']:
                    st.write(f"Due: {task['due_date']}")
                st.write(f"Status: {task['status']}")
                
                # Update task
                with st.form(f"update_task_{task['id']}"):
                    st.subheader("Update Task")
                    new_title = st.text_input("Title", value=task['title'], key=f"title_{task['id']}")
                    new_description = st.text_area("Description", value=task['description'], key=f"desc_{task['id']}")
                    new_due_date = st.date_input("Due Date", value=datetime.fromisoformat(task['due_date']) if task['due_date'] else None, key=f"due_{task['id']}")
                    new_priority = st.slider("Priority", 1, 5, value=task['priority'], key=f"priority_{task['id']}")
                    new_status = st.selectbox(
                        "Status",
                        ["pending", "in_progress", "completed"],
                        index=["pending", "in_progress", "completed"].index(task['status']),
                        key=f"status_{task['id']}"
                    )
                    
                    if st.form_submit_button("Update Task"):
                        try:
                            response = httpx.put(
                                f"{FASTAPI_URI}/tasks/{task['id']}",
                                json={
                                    "title": new_title,
                                    "description": new_description,
                                    "due_date": new_due_date.isoformat() if new_due_date else None,
                                    "priority": new_priority
                                },
                                params={"session_id": SESSION_ID},
                                verify=False
                            )
                            response.raise_for_status()
                            st.success("Task updated!")
                        except Exception as e:
                            st.error(f"Error updating task: {str(e)}")
                
                # Delete task
                if st.button("Delete Task", key=f"delete_{task['id']}"):
                    try:
                        response = httpx.delete(
                            f"{FASTAPI_URI}/tasks/{task['id']}",
                            params={"session_id": SESSION_ID},
                            verify=False
                        )
                        response.raise_for_status()
                        st.success("Task deleted!")
                        st.rerun()  # Refresh the page to show updated task list
                    except Exception as e:
                        st.error(f"Error deleting task: {str(e)}")
    except Exception as e:
        st.error(f"Error getting tasks: {str(e)}")

if __name__ == "__main__":
    show_task_manager() 