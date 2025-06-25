import redis
import json
import os

class RedisHistoryStore:
    def __init__(self, ttl=None):
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl  # Optional expiration for the entire list key

    def get_history(self, session_id: str, n_messages: int) -> list[dict]:
        """
        Retrieves the last n_messages from the conversation history list.
        """
        # LRANGE session_id -n -1 fetches the last n elements.
        raw_messages = self.redis.lrange(session_id, -n_messages, -1)
        if not raw_messages:
            return []
        
        # Messages are stored as JSON strings, so we need to decode them.
        return [json.loads(msg) for msg in raw_messages]

    def append_messages(self, session_id: str, messages: list[dict]):
        """
        Appends a list of messages to the history list in Redis using RPUSH.
        """
        # Using a pipeline is more efficient for multiple commands.
        pipe = self.redis.pipeline()
        for message in messages:
            pipe.rpush(session_id, json.dumps(message))
        
        # Refresh the TTL on each write to keep active conversations from expiring.
        if self.ttl:
            pipe.expire(session_id, self.ttl)
            
        pipe.execute()