import redis
import os

r = redis.Redis(host="localhost", port=6379, db=0)

def load_token(user_id, api_name):
    # Load when needed
    secrets = r.hgetall(f"token:{api_name}:{user_id}")
    
    if not secrets:
        raise ValueError(f"No token found for user_id: {user_id}")
    
    client_id = secrets[b"client_id"].decode()
    client_secret = secrets[b"client_secret"].decode()
    token = secrets[b"token"].decode()
    return token

def save_token(user_id, api_name, token):
    # Save once
    r.hset(f"token:{api_name}:{user_id}", mapping={
        "token": token
    })