import streamlit as st
st.set_page_config(page_title="Task Manager", page_icon="📝")
import httpx
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
FASTAPI_URI = os.getenv("FASTAPI_URI", "http://localhost:8000")

PRIORITY_LABELS = {0: "🔴 High", 1: "🟠 Medium", 2: "🟡 Low", 3: "🔵 Lowest"}
PRIORITY_ORDER = [0, 1, 2, 3]
STATUS_ORDER = ["pending", "in_progress", "completed"]
STATUS_LABELS = {
    "pending": "Pending",
    "in_progress": "In Progress",
    "completed": "Completed"
}

# Helper for color-coded priorities
def get_priority_label(priority):
    return PRIORITY_LABELS.get(priority, f"{priority}")

# Custom CSS for compact Jira-like cards
st.markdown("""
    <style>
    .task-card {
        background: #fff;
        border-left: 6px solid #888;
        border-radius: 6px;
        padding: 0.5rem 0.7rem 0.5rem 0.7rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        min-height: 60px;
    }
    .task-id {
        font-size: 0.75rem;
        color: #666;
        font-family: monospace;
        margin-bottom: 0.1rem;
    }
    .task-title {
        font-size: 0.98rem;
        font-weight: 600;
        margin-bottom: 0.1rem;
    }
    .task-desc {
        font-size: 0.8rem;
        color: #555;
        margin-bottom: 0.1rem;
    }
    .task-meta {
        font-size: 0.75rem;
        color: #888;
        margin-bottom: 0.1rem;
    }
    .stButton>button {
        padding: 0.15rem 0.6rem;
        font-size: 0.75rem;
        margin-right: 0.15rem;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 2400px;
    }
    /* Task card styling */
    .task-card {
        background: #fff;
        border-left: 6px solid #888;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        min-height: 70px;
        transition: all 0.2s ease;
    }
    .task-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    /* Make columns wider */
    [data-testid="column"] {
        min-width: 400px !important;
    }
    </style>
""", unsafe_allow_html=True)

def show_task_manager():
    st.title("📋 Task Manager")

    # Priority filter in main content area (moved from sidebar)
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("**Filters:**")
    with col2:
        priority_filter = st.selectbox(
            "Priority",
            options=["All"] + PRIORITY_ORDER,
            format_func=lambda x: get_priority_label(x) if isinstance(x, int) else x,
            index=0,
            label_visibility="collapsed"
        )
        if priority_filter == "All":
            priority_filter = None

    st.markdown("---")

    # --- New Task Modal ---
    if 'show_new_task' not in st.session_state:
        st.session_state['show_new_task'] = False
    if 'new_task_status' not in st.session_state:
        st.session_state['new_task_status'] = 'pending'

    def open_new_task():
        st.session_state['show_new_task'] = True
        st.session_state['new_task_status'] = 'pending'

    def close_new_task():
        st.session_state['show_new_task'] = False

    # --- Edit Task Modal ---
    if 'edit_task_id' not in st.session_state:
        st.session_state['edit_task_id'] = None
    if 'edit_task_data' not in st.session_state:
        st.session_state['edit_task_data'] = None

    def open_edit_task(task):
        st.session_state['edit_task_id'] = task['id']
        st.session_state['edit_task_data'] = task
        st.rerun()

    def close_edit_task():
        st.session_state['edit_task_id'] = None
        st.session_state['edit_task_data'] = None
        st.rerun()

    # --- Fetch Tasks ---
    params = {"session_id": st.session_state.session_token}
    if priority_filter is not None:
        params["priority"] = priority_filter
    try:
        response = httpx.get(
            f"{FASTAPI_URI}/tasks",
            params=params,
            verify=False
        )
        response.raise_for_status()
        tasks = response.json()
    except Exception as e:
        st.error(f"Error getting tasks: {str(e)}")
        tasks = []

    # --- Group tasks by status ---
    grouped = {status: [] for status in STATUS_ORDER}

    other_tasks = []
    for task in tasks:
        if task['status'] in grouped:
            grouped[task['status']].append(task)
        else:
            other_tasks.append(task)

    # Sort tasks within each status group
    for status in STATUS_ORDER:
        grouped[status].sort(key=lambda x: (x['priority'], x['due_date'] if x['due_date'] else '9999-12-31'))
        
    # Place a single + New Task button above the board
    st.button(
        "+ New Task",
        key="new_task_btn_main",
        on_click=open_new_task
    )

    # --- Kanban Board ---
    cols = st.columns([1, 1, 1], gap="large")  # Equal width columns
    for idx, status in enumerate(STATUS_ORDER):
        with cols[idx]:
            st.markdown(f"#### {STATUS_LABELS[status]}")
            for task in grouped[status]:
                border_color = PRIORITY_LABELS.get(task['priority'], "#888").split()[0]  # Emoji as color
                st.markdown(f'<div class="task-card" style="border-left-color:{border_color}">', unsafe_allow_html=True)
                st.markdown(f'<div class="task-id">{task["ticket_id"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="task-title">{task["title"]}</div>', unsafe_allow_html=True)
                # Show Gmail link if present
                if task.get("gmail_link"):
                    st.markdown(f'<div class="task-meta"><a href="{task["gmail_link"]}" target="_blank">📧 View Email</a></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="task-meta">{get_priority_label(task["priority"])} | Due: {task["due_date"][:10] if task["due_date"] else "-"}</div>', unsafe_allow_html=True)
                if task['description']:
                    st.markdown(f'<div class="task-desc">{task["description"]}</div>', unsafe_allow_html=True)
                
                # Show edit form if this task is being edited
                if st.session_state['edit_task_id'] == task['id']:
                    with st.form(f"edit_task_form_{task['id']}", clear_on_submit=True):
                        new_title = st.text_input("Title", value=task['title'])
                        new_description = st.text_area("Description", value=task['description'] or "")
                        new_due_date = st.date_input("Due Date", value=datetime.fromisoformat(task['due_date']) if task['due_date'] else None)
                        new_priority = st.selectbox(
                            "Priority",
                            options=PRIORITY_ORDER,
                            format_func=get_priority_label,
                            index=task['priority'] if task['priority'] in PRIORITY_ORDER else 0
                        )
                        new_status = st.selectbox(
                            "Status",
                            options=STATUS_ORDER,
                            format_func=lambda x: STATUS_LABELS[x],
                            index=STATUS_ORDER.index(task['status']) if task['status'] in STATUS_ORDER else 0
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Save"):
                                try:
                                    response = httpx.put(
                                        f"{FASTAPI_URI}/tasks/{task['id']}",
                                        json={
                                            "title": new_title,
                                            "description": new_description,
                                            "due_date": new_due_date.isoformat() if new_due_date else None,
                                            "priority": new_priority,
                                            "status": new_status
                                        },
                                        params={"session_id": st.session_state.session_token},
                                        verify=False
                                    )
                                    response.raise_for_status()
                                    st.success("Task updated!")
                                    close_edit_task()
                                except Exception as e:
                                    st.error(f"Error updating task: {str(e)}")
                        with col2:
                            if st.form_submit_button("Cancel"):
                                close_edit_task()
                else:
                    # Show edit/delete buttons if not editing
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Edit", key=f"edit_{task['id']}"):
                            open_edit_task(task)
                    with col2:
                        if st.button("Delete", key=f"delete_{task['id']}"):
                            try:
                                response = httpx.delete(
                                    f"{FASTAPI_URI}/tasks/{task['id']}",
                                    params={"session_id": st.session_state.session_token},
                                    verify=False
                                )
                                response.raise_for_status()
                                st.success("Task deleted!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting task: {str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)

    # --- New Task Modal (appears above board) ---
    if st.session_state['show_new_task']:
        st.markdown("---")
        st.subheader(f"✏️ New Task ({STATUS_LABELS[st.session_state['new_task_status']]})")
        with st.form("new_task_form", clear_on_submit=True):
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date", value=None)
            priority = st.selectbox(
                "Priority",
                options=PRIORITY_ORDER,
                format_func=get_priority_label,
                index=0
            )
            submitted = st.form_submit_button("Create")
            if submitted:
                if title:
                    try:
                        response = httpx.post(
                            f"{FASTAPI_URI}/tasks",
                            json={
                                "title": title,
                                "description": description,
                                "due_date": due_date.isoformat() if due_date else None,
                                "priority": priority,
                                "status": st.session_state['new_task_status']
                            },
                            params={"session_id": st.session_state.session_token},
                            verify=False
                        )
                        response.raise_for_status()
                        st.success("Task added successfully!")
                        st.session_state['show_new_task'] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding task: {str(e)}")
                else:
                    st.error("Title is required!")
            st.form_submit_button("Cancel", on_click=close_new_task)
        st.markdown("---")

    # --- Other Tasks (unexpected status) ---
    if other_tasks:
        st.markdown("### 🟣 Other Status Tasks (unexpected status value)")
        for task in other_tasks:
            st.markdown(f'<div class="task-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="task-title">{task["title"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="task-meta">Priority: {task["priority"]} | Status: {task["status"]}</div>', unsafe_allow_html=True)
            if task['description']:
                st.markdown(f'<div class="task-desc">{task["description"]}</div>', unsafe_allow_html=True)
            if task['due_date']:
                st.markdown(f'<div class="task-meta"><b>Due:</b> {task["due_date"][:10]}</div>', unsafe_allow_html=True)
            if st.button("Delete", key=f"delete_other_{task['id']}"):
                try:
                    response = httpx.delete(
                        f"{FASTAPI_URI}/tasks/{task['id']}",
                        params={"session_id": st.session_state.session_token},
                        verify=False
                    )
                    response.raise_for_status()
                    st.success("Task deleted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting task: {str(e)}")
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    show_task_manager()
