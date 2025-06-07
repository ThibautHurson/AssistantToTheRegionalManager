import streamlit as st
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

FASTAPI_URI = os.getenv("FASTAPI_URI")
SESSION_ID = os.getenv("SESSION_ID")

st.set_page_config(page_title="Chatbot", page_icon="🤖")

st.title("📬 Gmail-Integrated Chatbot")

# Session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 1. Check if user is authenticated
def check_auth():
    try:
        print(f"FASTAPI_URI value: {FASTAPI_URI}")
        print(f"Full URL being called: {FASTAPI_URI}/authorize")
        print(f"Session ID being sent: {SESSION_ID}")
        
        response = httpx.get(
            f"{FASTAPI_URI}/authorize",
            params={"session_id": SESSION_ID},
            follow_redirects=True,
            verify=False  # Only for testing, remove in production
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        data = response.json()
        print(f"Response data: {data}")
        
        if response.status_code == 200 and "Already authenticated" in data.get("message", ""):
            print("Already Authenticated")
            st.session_state.authenticated = True
        elif response.status_code == 307:
            auth_url = response.headers["location"]
            st.markdown(f"Please [authenticate with Google]({auth_url}) to continue.")
        else:
            st.error(f"Failed to check auth status. Status code: {response.status_code}")
    except httpx.ReadTimeout:
        st.error("Request timed out. The server took too long to respond.")
        print("Read timeout error")
    except httpx.ConnectTimeout:
        st.error("Connection to backend timed out. Please ensure the backend service is running.")
        print("Connection timeout error")
    except httpx.ConnectError:
        st.error("Could not connect to backend service. Please ensure it's running.")
        print("Connection error")
    except Exception as e:
        st.error(f"Auth error: {e}")
        print(f"Unexpected error: {e}")

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
    show_chat()