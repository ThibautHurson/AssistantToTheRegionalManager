import functools
import httpx
import json

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