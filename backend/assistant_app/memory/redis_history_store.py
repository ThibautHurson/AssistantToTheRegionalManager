import sys
print(sys.executable)

import redis
import json

class RedisHistoryStore:
    def __init__(self, redis_url="redis://127.0.0.1:6379", ttl=None):
        self.redis = redis.Redis.from_url(redis_url)
        self.ttl = ttl  # Optional expiration (in seconds)

    def get(self, session_id: str) -> list[dict]:
        raw = self.redis.get(session_id)
        if not raw:
            return []
        history_data = json.loads(raw)
        return history_data

    def save(self, session_id: str, history: list[dict]):
        self.redis.set(session_id, json.dumps(history))
        if self.ttl:
            self.redis.expire(session_id, self.ttl)