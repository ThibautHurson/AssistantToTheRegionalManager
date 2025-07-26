import streamlit as st
import httpx
import os
from dotenv import load_dotenv
from backend.assistant_app.utils.redis_saver import load_chat_sessions_from_redis, load_current_session_from_redis
from backend.assistant_app.utils.logger import streamlit_logger

load_dotenv()
FASTAPI_URI = os.getenv("FASTAPI_URI", "http://localhost:8000")

def show_login_form():
    """Display login form."""
    st.markdown("### 🔐 Login")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            if email and password:
                try:
                    response = httpx.post(
                        f"{FASTAPI_URI}/auth/login",
                        json={"email": email, "password": password},
                        timeout=10
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            # Store session token in session state
                            st.session_state.session_token = data.get("session_token")
                            st.session_state.user_email = data.get("user_email")
                            st.session_state.authenticated = True

                            # Load chat sessions from Redis
                            try:
                                chat_sessions = load_chat_sessions_from_redis(data.get("user_email"))
                                if chat_sessions:
                                    st.session_state.chat_sessions = chat_sessions
                                    # Load current session ID
                                    current_session_id = load_current_session_from_redis(data.get("user_email"))
                                    if current_session_id and current_session_id in chat_sessions:
                                        st.session_state.current_session_id = current_session_id
                                    else:
                                        # Set to first session if current session doesn't exist
                                        first_session_id = list(chat_sessions.keys())[0] if chat_sessions else None
                                        st.session_state.current_session_id = first_session_id
                                else:
                                    st.session_state.chat_sessions = {}
                                    st.session_state.current_session_id = None
                            except Exception as e:
                                streamlit_logger.log_error(e, {"context": "load_chat_sessions"})
                                st.session_state.chat_sessions = {}
                                st.session_state.current_session_id = None

                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error(data.get("message", "Login failed"))
                    else:
                        error_data = response.json()
                        st.error(error_data.get("detail", "Login failed"))

                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
            else:
                st.error("Please enter both email and password")

def show_register_form():
    """Display registration form."""
    st.markdown("### 📝 Register")

    with st.form("register_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password", placeholder="Choose a password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        submit_button = st.form_submit_button("Register")

        if submit_button:
            if email and password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    try:
                        response = httpx.post(
                            f"{FASTAPI_URI}/auth/register",
                            json={"email": email, "password": password},
                            timeout=10
                        )

                        if response.status_code == 200:
                            data = response.json()
                            if data.get("success"):
                                st.success("Registration successful! Please log in.")
                                st.session_state.show_login = True
                                st.rerun()
                            else:
                                st.error(data.get("message", "Registration failed"))
                        else:
                            error_data = response.json()
                            st.error(error_data.get("detail", "Registration failed"))

                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")
            else:
                st.error("Please fill in all fields")

def show_auth_page():
    """Main authentication page with login/register tabs."""
    st.title("🔐 Authentication")
    st.markdown("Welcome! Please log in or create a new account to continue.")

    # Initialize session state
    if "show_login" not in st.session_state:
        st.session_state.show_login = True

    # Create tabs for login and register
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        show_login_form()

    with tab2:
        show_register_form()

def logout_user():
    """Logout the current user."""
    if "session_token" in st.session_state:
        try:
            response = httpx.post(
                f"{FASTAPI_URI}/auth/logout",
                params={"session_token": st.session_state.session_token},
                timeout=10
            )
            if response.status_code == 200:
                st.success("Logged out successfully")
        except Exception as e:
            st.error(f"Logout error: {str(e)}")

    # Clear authentication-related session state but preserve chat sessions
    auth_keys_to_clear = ["session_token", "user_email", "authenticated", "chat_history", "chat_session_id", "message_limit"]
    for key in auth_keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # Note: chat_sessions and current_session_id are preserved in session state
    # but will be reloaded from Redis upon next login

    st.rerun()

def validate_session():
    """Validate current session and return user info."""
    if "session_token" not in st.session_state:
        return None

    try:
        response = httpx.get(
            f"{FASTAPI_URI}/auth/validate",
            params={"session_token": st.session_state.session_token},
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            # Session is invalid, clear authentication data but preserve chat sessions
            auth_keys_to_clear = ["session_token", "user_email", "authenticated", "chat_history", "chat_session_id", "message_limit"]
            for key in auth_keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            return None

    except Exception as e:
        streamlit_logger.log_error(e, {"context": "session_validation"})
        return None