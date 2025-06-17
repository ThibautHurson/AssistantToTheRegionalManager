import streamlit as st
import os
import httpx
from dotenv import load_dotenv
from task_manager import show_task_manager

load_dotenv()

FASTAPI_URI = os.getenv("FASTAPI_URI")
SESSION_ID = os.getenv("SESSION_ID")

st.set_page_config(
    page_title="Chatbot", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded")

st.title("📬 Gmail-Integrated Chatbot")

# Session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def check_auth():
    """Check if user is authenticated with Google"""
    try:
        auth_response = httpx.get(
            f"{FASTAPI_URI}/authorize",
            params={"session_id": SESSION_ID},
            verify=False  # Only for testing, remove in production
        )
        auth_response.raise_for_status()
        auth_data = auth_response.json()
        
        if "auth_url" in auth_data:
            st.markdown(f"Please complete the Google authentication process by visiting this URL: [Click here to authenticate]({auth_data['auth_url']})")
            st.stop()
        elif "error" in auth_data:
            st.error(f"Authentication error: {auth_data['error']}")
            st.stop()
        else:
            st.session_state.authenticated = True
    except httpx.HTTPError as e:
        st.error(f"Error: {str(e)}")
        st.stop()

# 2. Display chat UI
def show_chat():
    user_input = st.text_input("You:", key="user_input")

    if user_input:
        try:
            print("Going to call /chat endpoint")
            res = httpx.post(
                f"{FASTAPI_URI}/chat",
                json={"session_id": SESSION_ID, "input": user_input},
                timeout=120
            )
            res.raise_for_status()
            bot_reply = res.json()["response"]

            st.session_state.chat_history.append(("You", user_input))
            st.session_state.chat_history.append(("Bot", bot_reply))
        except Exception as e:
            st.error(f"Error: {e}")

    for sender, msg in st.session_state.chat_history:
        st.markdown(f"**{sender}:** {msg}")

# Entry point
if not st.session_state.authenticated:
    check_auth()

if st.session_state.authenticated:
    # Create tabs for different functionalities
    tab1, tab2 = st.tabs(["Chat", "Task Manager"])
    
    with tab1:
        show_chat()
    
    with tab2:
        show_task_manager()