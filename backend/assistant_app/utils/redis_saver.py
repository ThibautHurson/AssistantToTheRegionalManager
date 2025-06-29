import redis
import os
import json

redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
r = redis.Redis.from_url(redis_url)

def load_from_redis(user_id, key_name):
    # Load when needed
    last_history_id = r.get(f"{key_name}:{user_id}")
    
    if last_history_id:
        return last_history_id.decode()
    return None
    

def save_to_redis(user_id, key_name, value):
    r.set(f"{key_name}:{user_id}", value)

def save_chat_sessions_to_redis(user_email, chat_sessions):
    """Save chat sessions to Redis for a specific user."""
    try:
        sessions_json = json.dumps(chat_sessions)
        r.set(f"chat_sessions:{user_email}", sessions_json)
        return True
    except Exception as e:
        print(f"Error saving chat sessions to Redis: {e}")
        return False

def load_chat_sessions_from_redis(user_email):
    """Load chat sessions from Redis for a specific user."""
    try:
        sessions_json = r.get(f"chat_sessions:{user_email}")
        if sessions_json:
            return json.loads(sessions_json.decode())
        return {}
    except Exception as e:
        print(f"Error loading chat sessions from Redis: {e}")
        return {}

def save_current_session_to_redis(user_email, current_session_id):
    """Save the current session ID to Redis."""
    try:
        r.set(f"current_session:{user_email}", current_session_id)
        return True
    except Exception as e:
        print(f"Error saving current session to Redis: {e}")
        return False

def load_current_session_from_redis(user_email):
    """Load the current session ID from Redis."""
    try:
        current_session = r.get(f"current_session:{user_email}")
        if current_session:
            return current_session.decode()
        return None
    except Exception as e:
        print(f"Error loading current session from Redis: {e}")
        return None