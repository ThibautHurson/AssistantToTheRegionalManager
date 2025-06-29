import streamlit as st
import httpx
import os
from dotenv import load_dotenv

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
    
    # Clear session state
    for key in ["session_token", "user_email", "authenticated", "chat_history", "chat_session_id", "message_limit"]:
        if key in st.session_state:
            del st.session_state[key]
    
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
            # Session is invalid, clear it
            for key in ["session_token", "user_email", "authenticated", "chat_history", "chat_session_id", "message_limit"]:
                if key in st.session_state:
                    del st.session_state[key]
            return None
            
    except Exception as e:
        print(f"Session validation error: {e}")
        return None 