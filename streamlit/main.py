import streamlit as st
import os
import httpx
from dotenv import load_dotenv
from task_manager import show_task_manager
import redis
from backend.assistant_app.utils.redis_saver import save_to_redis, load_from_redis
import json
from auth_ui import show_auth_page, logout_user, validate_session

load_dotenv()

FASTAPI_URI = os.getenv("FASTAPI_URI")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

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
    /* Lighter text color for prompt text areas only */
    .prompt-manager .stTextArea textarea {
        color: #666666 !important;
        font-family: 'Courier New', monospace !important;
        max-height: none !important;
        min-height: 600px !important;
    }
    /* Specific styling for prompt manager text areas */
    .prompt-manager .stTextArea textarea {
        max-height: none !important;
        min-height: 600px !important;
    }
    /* Override general textarea rules for prompt manager */
    .prompt-manager textarea {
        max-height: none !important;
        min-height: 600px !important;
        color: #666666 !important;
        font-family: 'Courier New', monospace !important;
    }
    /* Target Streamlit's specific text area elements in prompt manager */
    .prompt-manager [data-testid="stTextArea"] textarea {
        max-height: none !important;
        min-height: 600px !important;
        color: #666666 !important;
        font-family: 'Courier New', monospace !important;
    }
    .prompt-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .prompt-title {
        font-weight: 600;
        color: #495057;
        margin-bottom: 0.5rem;
    }
    .prompt-content {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 4px;
        padding: 0.75rem;
        font-family: monospace;
        font-size: 0.9rem;
        white-space: pre-wrap;
        max-height: 200px;
        overflow-y: auto;
    }
    /* Clean info box styling */
    .stInfo {
        background-color: #e3f2fd !important;
        border: 1px solid #2196f3 !important;
        border-radius: 8px !important;
        padding: 0.5rem !important;
        margin-bottom: 1rem !important;
    }
    /* Button styling for message toggle */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    .main .block-container {
        padding-top: 0.2rem !important;
    }
    /* Make title more compact */
    h1 {
        margin-top: 0.2rem !important;
        margin-bottom: 0.8rem !important;
        font-size: 1.8rem !important;
        padding-top: 0 !important;
    }
    /* Remove extra spacing from Streamlit elements */
    .stMarkdown {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📬 Gmail-Integrated Chatbot")

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Message display control
if "message_limit" not in st.session_state:
    st.session_state.message_limit = 5  # Default to show last 5 messages

def check_oauth_auth():
    """Check if user has OAuth authentication for Gmail"""
    if not st.session_state.authenticated or "session_token" not in st.session_state:
        return False
    
    try:
        auth_response = httpx.get(
            f"{FASTAPI_URI}/authorize",
            params={"session_token": st.session_state.session_token},
            verify=False
        )
        auth_response.raise_for_status()
        auth_data = auth_response.json()
        
        if "auth_url" in auth_data:
            st.markdown("### 🔗 Gmail Authentication Required")
            st.markdown("To use Gmail features, please authenticate with Google:")
            st.markdown(f"[Click here to authenticate with Google]({auth_data['auth_url']})")
            st.markdown("After authentication, you'll be redirected back to the app.")
            return False
        elif "error" in auth_data:
            st.error(f"Authentication error: {auth_data['error']}")
            return False
        else:
            return True
    except httpx.HTTPError as e:
        st.error(f"Error: {str(e)}")
        return False

def show_chat():
    """Display chat interface."""
    # Check OAuth authentication first
    if not check_oauth_auth():
        return
    
    # Initialize chat session ID if not exists
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = None
    
    # New Chat button
    if st.button("🆕 New Chat"):
        st.session_state.chat_session_id = None
        st.session_state.chat_history = []
        st.session_state.message_limit = 5
        st.rerun()
    
    # Clean message display controls
    total_messages = len(st.session_state.chat_history)
    
    # Message display controls
    if total_messages > 5:  # Only show controls if there are many messages
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.info(f"📋 Showing last {st.session_state.message_limit} of {total_messages} messages")
        
        with col2:
            # Show "Show 5 More" button if there are more messages to load
            if total_messages > st.session_state.message_limit:
                if st.button("Show 5 More"):
                    st.session_state.message_limit = min(st.session_state.message_limit + 5, total_messages)
                    st.rerun()
        
        with col3:
            # Show "Show Recent" button if we're showing more than 5 messages
            if st.session_state.message_limit > 5:
                if st.button("Show Recent"):
                    st.session_state.message_limit = 5
                    st.rerun()
    
    # Chat container for messages
    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Determine which messages to display
        messages_to_display = st.session_state.chat_history[-st.session_state.message_limit:]
        
        # Display chat messages in normal order (oldest at top, newest at bottom)
        for sender, msg in messages_to_display:
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
    
    if send_clicked and user_input:
        try:
            print("Going to call /chat endpoint")
            # Append user message first for immediate feedback
            st.session_state.chat_history.append(("You", user_input))

            # Prepare request payload
            payload = {
                "session_token": st.session_state.session_token, 
                "input": user_input
            }
            
            # Add chat session ID if we have one
            if st.session_state.chat_session_id:
                payload["chat_session_id"] = st.session_state.chat_session_id

            res = httpx.post(
                f"{FASTAPI_URI}/chat",
                json=payload,
                timeout=120
            )
            res.raise_for_status()
            response_data = res.json()
            bot_reply = response_data["response"]
            
            # Store the chat session ID if provided
            if "chat_session_id" in response_data:
                st.session_state.chat_session_id = response_data["chat_session_id"]

            st.session_state.chat_history.append(("Bot", bot_reply))
            st.rerun() # Rerun to show the bot's reply
        except Exception as e:
            st.error(f"Error: {e}")
            # Optional: remove the user's message if the call failed
            # st.session_state.chat_history.pop()

def show_prompt_manager():
    """Display prompt management interface"""
    st.title("🎭 Prompt Manager")
    st.markdown("Manage and view MCP prompt templates that control the assistant's behavior.")
    
    # Wrap in div with CSS class for specific styling
    st.markdown('<div class="prompt-manager">', unsafe_allow_html=True)
    
    # Create tabs for different prompt management features
    tab1, tab2, tab3 = st.tabs(["View Prompts", "Edit Prompts", "Create New"])
    
    with tab1:
        # Get available prompts using direct API
        try:
            response = httpx.get(
                f"{FASTAPI_URI}/prompts",
                timeout=30
            )
            response.raise_for_status()
            prompts_data = response.json()
            
            if "prompts" in prompts_data:
                prompts_text = prompts_data["prompts"]
                
                # Parse the prompts text to extract individual prompts
                if "Available prompt templates:" in prompts_text:
                    prompt_lines = prompts_text.split("Available prompt templates:")[1].strip().split("\n")
                    prompts = [line.strip("- ") for line in prompt_lines if line.strip().startswith("-")]
                    
                    st.subheader("Available Prompt Templates")
                    
                    # Create tabs for each prompt
                    if prompts:
                        prompt_names = [prompt.strip() for prompt in prompts]
                        prompt_tabs = st.tabs(prompt_names)
                        
                        for i, (tab, prompt_name) in enumerate(zip(prompt_tabs, prompt_names)):
                            with tab:
                                st.markdown(f"**{prompt_name}**")
                                
                                # Get the actual prompt content using direct API
                                try:
                                    content_response = httpx.get(
                                        f"{FASTAPI_URI}/prompts/{prompt_name}",
                                        timeout=30
                                    )
                                    content_response.raise_for_status()
                                    content_data = content_response.json()
                                    
                                    if "prompt" in content_data:
                                        # Display the prompt content in a text area
                                        st.text_area(
                                            "Prompt Content:",
                                            value=content_data["prompt"],
                                            height=600,
                                            disabled=True,
                                            label_visibility="collapsed"
                                        )
                                    else:
                                        st.error("No prompt content received")
                                        
                                except Exception as e:
                                    st.error(f"Error retrieving prompt content: {e}")
                    else:
                        st.info("No prompt templates found.")
                else:
                    st.info("Could not parse prompt templates.")
            else:
                st.info("No prompt data received.")
                
        except Exception as e:
            st.error(f"Error connecting to prompt manager: {e}")
    
    with tab2:
        st.subheader("Edit Existing Prompts")
        st.markdown("Modify existing prompt templates.")
        
        # Get current prompts for selection using direct API
        try:
            response = httpx.get(
                f"{FASTAPI_URI}/prompts",
                timeout=30
            )
            response.raise_for_status()
            prompts_data = response.json()
            
            if "prompts" in prompts_data:
                prompts_text = prompts_data["prompts"]
                
                if "Available prompt templates:" in prompts_text:
                    prompt_lines = prompts_text.split("Available prompt templates:")[1].strip().split("\n")
                    prompts = [line.strip("- ") for line in prompt_lines if line.strip().startswith("-")]
                    prompt_names = [prompt.strip() for prompt in prompts]
                    
                    selected_prompt = st.selectbox("Select prompt to edit:", prompt_names)
                    
                    if selected_prompt:
                        # Get current content using direct API
                        try:
                            content_response = httpx.get(
                                f"{FASTAPI_URI}/prompts/{selected_prompt}",
                                timeout=30
                            )
                            content_response.raise_for_status()
                            content_data = content_response.json()
                            
                            if "prompt" in content_data:
                                current_content = content_data["prompt"]
                                
                                with st.form("edit_prompt"):
                                    new_content = st.text_area(
                                        "Edit prompt content:",
                                        value=current_content,
                                        height=500
                                    )
                                    
                                    if st.form_submit_button("Update Prompt"):
                                        try:
                                            update_response = httpx.put(
                                                f"{FASTAPI_URI}/prompts/{selected_prompt}",
                                                json={
                                                    "prompt_name": selected_prompt,
                                                    "content": new_content
                                                },
                                                timeout=60
                                            )
                                            update_response.raise_for_status()
                                            update_data = update_response.json()
                                            
                                            if "message" in update_data:
                                                st.success(update_data["message"])
                                            else:
                                                st.error("No response message received")
                                            
                                        except Exception as e:
                                            st.error(f"Error updating prompt: {e}")
                            else:
                                st.error("No prompt content received")
                                
                        except Exception as e:
                            st.error(f"Error retrieving prompt content: {e}")
                else:
                    st.info("No prompts available for editing.")
            else:
                st.info("No prompt data received.")
                
        except Exception as e:
            st.error(f"Error loading prompts: {e}")
    
    with tab3:
        st.subheader("Create New Prompt Template")
        st.markdown("Create a new prompt template for specialized use cases.")
        
        with st.form("create_prompt"):
            new_prompt_name = st.text_input("Prompt name (without .md extension):")
            new_prompt_content = st.text_area(
                "Prompt content (supports Markdown formatting):",
                height=500,
                placeholder="Enter the prompt content here...\n\n# Title\n## Section\n- **Bold text**\n- *Italic text**\n- `code`"
            )
            
            if st.form_submit_button("Create Prompt"):
                if new_prompt_name and new_prompt_content:
                    try:
                        create_response = httpx.post(
                            f"{FASTAPI_URI}/prompts",
                            json={
                                "prompt_name": new_prompt_name,
                                "content": new_prompt_content
                            },
                            timeout=60
                        )
                        create_response.raise_for_status()
                        create_data = create_response.json()
                        
                        if "message" in create_data:
                            st.success(create_data["message"])
                        else:
                            st.error("No response message received")
                        
                    except Exception as e:
                        st.error(f"Error creating prompt: {e}")
                else:
                    st.warning("Please provide both a name and content for the new prompt.")
    
    # Close the CSS wrapper div
    st.markdown('</div>', unsafe_allow_html=True)

# Main application logic
def main():
    # Check if user is authenticated
    if not st.session_state.authenticated:
        # Validate existing session if available
        user_info = validate_session()
        if user_info:
            st.session_state.authenticated = True
            st.session_state.user_email = user_info.get("email")
        else:
            # Show authentication page
            show_auth_page()
            return
    
    # User is authenticated, show main interface
    # Sidebar with user info and logout
    with st.sidebar:
        st.markdown(f"**Welcome, {st.session_state.user_email}!**")
        if st.button("Logout"):
            logout_user()
            return
    
    # Create tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(["Chat", "Task Manager", "Prompt Manager"])
    
    with tab1:
        show_chat()
    
    with tab2:
        show_task_manager()
    
    with tab3:
        show_prompt_manager()

    # Save chat history after every message
    if st.session_state.chat_history:
        save_to_redis(st.session_state.user_email, "chat_history", json.dumps(st.session_state.chat_history))

if __name__ == "__main__":
    main()