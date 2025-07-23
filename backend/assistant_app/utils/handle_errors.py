import functools
import httpx
import json
import time
from mistralai.models import sdkerror
import asyncio
from functools import wraps
from googleapiclient.errors import HttpError
from typing import Callable, Any, Union, List, Type

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

def retry_on_rate_limit_async(
    max_attempts: int = 5,
    wait_seconds: int = 1,
    retry_on: Union[Type[Exception], List[Type[Exception]]] = None,
    retry_on_status: List[int] = None,
    return_none_on_404: bool = False
):
    """Decorator to retry async functions on rate limit errors and other specified errors.

    Args:
        max_attempts: Maximum number of retry attempts
        wait_seconds: Base wait time between retries (will be multiplied by 2^attempt)
        retry_on: Exception type(s) to retry on
        retry_on_status: HTTP status codes to retry on
        return_none_on_404: Whether to return None on 404 errors instead of retrying
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Handle HttpError (Gmail API)
                    if isinstance(e, HttpError):
                        if e.resp.status == 404 and return_none_on_404:
                            print("Resource not found (404)")
                            return None
                        if retry_on_status and e.resp.status in retry_on_status:
                            if attempt < max_attempts - 1:
                                wait = wait_seconds * (2 ** attempt)
                                print(f"Retrying after {wait}s (attempt {attempt + 1}/{max_attempts})")
                                await asyncio.sleep(wait)
                                continue
                        print(f"HTTP error: {e}")
                        return None

                    # Handle SDKError (Mistral)
                    if isinstance(e, sdkerror.SDKError):
                        if "429" in str(e) or "rate limit" in str(e).lower():
                            wait = wait_seconds * (2 ** attempt)
                            await asyncio.sleep(wait)
                            continue
                        raise

                    # Handle other specified exceptions
                    if retry_on and isinstance(e, retry_on):
                        if attempt < max_attempts - 1:
                            wait = wait_seconds * (2 ** attempt)
                            print(f"Retrying after {wait}s (attempt {attempt + 1}/{max_attempts})")
                            await asyncio.sleep(wait)
                            continue

                    # If we get here, either we're out of retries or it's an unhandled error
                    if attempt == max_attempts - 1:
                        raise Exception(f"Retry failed after {max_attempts} attempts: {str(e)}")
                    raise
            return None
        return wrapper
    return decorator