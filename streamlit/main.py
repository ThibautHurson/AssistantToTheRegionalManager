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

# Custom CSS for chat bubbles and layout
st.markdown("""
    <style>
    .chat-container {
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        min-height: 100px;
        max-height: 60vh;
        overflow-y: auto;
        width: 100%;
    }
    .chat-bubble {
        padding: 10px 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 80%;
        clear: both;
        word-break: break-word;
    }
    .user-bubble {
        background-color: #DCF8C6;
        align-self: flex-end;
        float: right;
    }
    .bot-bubble {
        background-color: #F1F0F0;
        align-self: flex-start;
        float: left;
    }
    .stTextInput, textarea {
        border-radius: 15px !important;
        padding: 10px !important;
        font-size: 1rem !important;
        min-height: 40px !important;
        max-height: 200px !important;
        resize: vertical !important;
        width: 80%;
    }
    </style>
""", unsafe_allow_html=True)

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
    # Chat container for messages
    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Display chat messages in normal order (oldest at top, newest at bottom)
        for sender, msg in st.session_state.chat_history:
            if sender == "You":
                st.markdown(f'<div class="chat-bubble user-bubble"><b>You:</b> {msg}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'**Bot:** {msg}', unsafe_allow_html=False)
                
        st.markdown('</div>', unsafe_allow_html=True)

    # Chat input at the bottom
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "You:",
            key="user_input",
            label_visibility="collapsed",
            placeholder="Ask me anything...",
            height=100,
        )
        send_clicked = st.form_submit_button("Send")
    print(send_clicked, user_input)
    if send_clicked and user_input:
        try:
            print("Going to call /chat endpoint")
            # Append user message first for immediate feedback
            st.session_state.chat_history.append(("You", user_input))

            res = httpx.post(
                f"{FASTAPI_URI}/chat",
                json={"session_id": SESSION_ID, "input": user_input},
                timeout=120
            )
            res.raise_for_status()
            bot_reply = res.json()["response"]

            st.session_state.chat_history.append(("Bot", bot_reply))
            st.rerun() # Rerun to show the bot's reply
        except Exception as e:
            st.error(f"Error: {e}")
            # Optional: remove the user's message if the call failed
            # st.session_state.chat_history.pop()

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