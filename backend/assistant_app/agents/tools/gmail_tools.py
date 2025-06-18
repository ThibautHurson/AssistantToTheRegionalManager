from dotenv import load_dotenv
import os
import json
import base64
from backend.assistant_app.utils.tool_registry import register_tool
from backend.assistant_app.utils.handle_errors import retry_on_rate_limit_async

load_dotenv()
SESSION_ID = os.getenv("SESSION_ID")
MAX_RESULTS = 10

@retry_on_rate_limit_async(
    max_attempts=3,
    wait_seconds=2,
    retry_on_status=[429, 500, 502, 503, 504],
    return_none_on_404=True
)
async def get_gmail(service, message_id):
    """Get Gmail message content with retry logic, and return payload, history_id, and labels."""
    msg_data = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    payload = msg_data['payload']
    history_id = msg_data['historyId']
    labels = msg_data.get('labelIds', [])

    def get_parts(part):
        if 'parts' in part:
            for sub_part in part['parts']:
                yield from get_parts(sub_part)
        elif part.get('mimeType') == 'text/plain' and 'data' in part['body']:
            yield base64.urlsafe_b64decode(part['body']['data']).decode()

    return "\n".join(get_parts(payload)), history_id, labels

@retry_on_rate_limit_async(
    max_attempts=3,
    wait_seconds=2,
    retry_on_status=[429, 500, 502, 503, 504],
    return_none_on_404=True
)
async def _search_gmail(service, query: str):
    """Search Gmail with retry logic."""
    results = service.users().messages().list(userId='me', q=query, maxResults=MAX_RESULTS).execute()
    messages = results.get('messages', [])
    messages_payload = []

    for msg in messages[:MAX_RESULTS]:
        content, _, _ = await get_gmail(service, msg['id'])
        if content:
            messages_payload.append(content)
    return json.dumps(messages_payload)

# Exposed tool to the agent (LLM sees only this interface)
@register_tool
async def search_gmail(query: str):
    """Search Gmail messages with retry logic."""
    from backend.assistant_app.api_integration.google_token_store import load_credentials
    from googleapiclient.discovery import build

    creds = load_credentials(SESSION_ID)
    service = build("gmail", "v1", credentials=creds)

    return await _search_gmail(service, query)