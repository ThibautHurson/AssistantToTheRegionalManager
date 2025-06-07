from dotenv import load_dotenv
import os
import json
import base64
from backend.assistant_app.utils.tool_registry import register_tool

load_dotenv()
SESSION_ID = os.getenv("SESSION_ID")
MAX_RESULTS = 10

def get_gmail(service, message_id):
    msg_data = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    payload = msg_data['payload']

    def get_parts(part):
        if 'parts' in part:
            for sub_part in part['parts']:
                yield from get_parts(sub_part)
        elif part.get('mimeType') == 'text/plain' and 'data' in part['body']:
            yield base64.urlsafe_b64decode(part['body']['data']).decode()

    return "\n".join(get_parts(payload))

def _search_gmail(service, query: str):
    results = service.users().messages().list(userId='me', q=query, maxResults=MAX_RESULTS).execute()
    messages = results.get('messages', [])
    messages_payload = []

    for msg in messages[:MAX_RESULTS]:
        messages_payload.append(get_gmail(service, msg['id']))
    return json.dumps(messages_payload)

# Exposed tool to the agent (LLM sees only this interface)
@register_tool
def search_gmail(query: str):
    from backend.assistant_app.api_integration.google_token_store import load_credentials
    from googleapiclient.discovery import build

    creds = load_credentials(SESSION_ID)
    service = build("gmail", "v1", credentials=creds)

    return _search_gmail(service, query)    