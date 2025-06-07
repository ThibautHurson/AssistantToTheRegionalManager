import redis
import os

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