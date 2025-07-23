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
        print(f"Getting history for Redis key: {session_id}, n_messages: {n_messages}")
        # LRANGE session_id -n -1 fetches the last n elements.
        raw_messages = self.redis.lrange(session_id, -n_messages, -1)
        if not raw_messages:
            print(f"No messages found for Redis key: {session_id}")
            return []

        print(f"Found {len(raw_messages)} messages for Redis key: {session_id}")
        # Messages are stored as JSON strings, so we need to decode them.
        return [json.loads(msg) for msg in raw_messages]

    def append_messages(self, session_id: str, messages: list[dict]):
        """
        Appends a list of messages to the history list in Redis using RPUSH.
        """
        print(f"Appending {len(messages)} messages to Redis key: {session_id}")
        # Using a pipeline is more efficient for multiple commands.
        pipe = self.redis.pipeline()
        for message in messages:
            pipe.rpush(session_id, json.dumps(message))

        # Refresh the TTL on each write to keep active conversations from expiring.
        if self.ttl:
            pipe.expire(session_id, self.ttl)

        pipe.execute()
        print(f"Successfully appended messages to Redis key: {session_id}")

    def delete_history(self, user_id: str) -> int:
        """
        Delete all session history for a specific user based on user ID (email).

        Args:
            user_id: User's email address to identify their sessions

        Returns:
            int: Number of Redis keys deleted
        """
        if not user_id:
            print("No user_id provided for delete_history")
            return 0

        try:
            keys_to_delete = []

            # Find all Redis keys that start with the user's email
            # Session IDs are in format: {user.email}_{uuid}
            pattern = f"{user_id}_*"
            session_keys = self.redis.keys(pattern)
            keys_to_delete.extend(session_keys)

            # Also find summary keys for this user
            summary_pattern = f"summary:{user_id}_*"
            summary_keys = self.redis.keys(summary_pattern)
            keys_to_delete.extend(summary_keys)

            # Clear chat sessions metadata
            chat_sessions_key = f"chat_sessions:{user_id}"
            if self.redis.exists(chat_sessions_key):
                keys_to_delete.append(chat_sessions_key)

            # Clear current session reference
            current_session_key = f"current_session:{user_id}"
            if self.redis.exists(current_session_key):
                keys_to_delete.append(current_session_key)

            # Clear OAuth state
            oauth_state_key = f"{user_id}:oauth_state"
            if self.redis.exists(oauth_state_key):
                keys_to_delete.append(oauth_state_key)

            # Clear Google credentials
            google_creds_key = f"google_creds:{user_id}"
            if self.redis.exists(google_creds_key):
                keys_to_delete.append(google_creds_key)

            if keys_to_delete:
                # Delete all keys in a single operation
                deleted_count = self.redis.delete(*keys_to_delete)
                print(f"Deleted {deleted_count} Redis keys for user {user_id}")
                print(f"Deleted keys: {keys_to_delete}")
                return deleted_count
            else:
                print(f"No Redis keys found for user {user_id}")
                return 0

        except Exception as e:
            print(f"Error deleting history for user {user_id}: {e}")
            return 0

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session's history.

        Args:
            session_id: The specific session ID to delete

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            # Delete the session history
            result = self.redis.delete(session_id)

            # Also delete the summary if it exists
            summary_key = f"summary:{session_id}"
            self.redis.delete(summary_key)

            if result > 0:
                print(f"Deleted session history for {session_id}")
                return True
            else:
                print(f"No session history found for {session_id}")
                return False

        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False
