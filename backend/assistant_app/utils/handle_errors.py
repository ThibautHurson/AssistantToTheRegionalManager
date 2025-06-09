import functools
import httpx
import json
import time
from mistralai.models import sdkerror
import asyncio

def handle_httpx_errors(func):
    @functools.wraps(func)
    def wrapper(*arg, **kwargs):
        try:
            response = func(*arg, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP Status Error {e.response.status_code} - {e.response.text}"})
        except httpx.RequestError as e:
            return json.dumps({"error": f"Request Error - {e}"})
        except Exception as e:
            return json.dumps({"error": f"Unknown Error - {e}"})
    return wrapper

def retry_on_rate_limit(max_attempts=5, wait_seconds=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except sdkerror.SDKError as e:
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        time.sleep(wait_seconds)
                    else:
                        raise e
        return wrapper
    return decorator

def retry_on_rate_limit_async(max_attempts=5, wait_seconds=1):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except sdkerror.SDKError as e:
                    last_error = e
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        wait = wait_seconds * (2 ** attempt)
                        await asyncio.sleep(wait)
                    else:
                        raise
            raise Exception(f"Rate limit retry failed after {max_attempts} attempts.")
        return wrapper
    return decorator