from dotenv import load_dotenv
import os
import httpx
import json
from backend.assistant_app.utils.handle_errors import handle_httpx_errors
import base64
from backend.assistant_app.utils.tool_registry import register_tool

load_dotenv()

def _search_gmail(service, query: str):
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    messages_payload = []

    for msg in messages[:2]:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_data['payload']

        def get_parts(part):
            if 'parts' in part:
                for sub_part in part['parts']:
                    yield from get_parts(sub_part)
            elif part.get('mimeType') == 'text/plain' and 'data' in part['body']:
                yield base64.urlsafe_b64decode(part['body']['data']).decode()

        messages_payload.append("\n".join(get_parts(payload)))
    return json.dumps(messages_payload[:1000])

# Exposed tool to the agent (LLM sees only this interface)
@register_tool
def search_gmail(query: str):
    from backend.assistant_app.api_integration.google_token_store import get_google_credencials
    from googleapiclient.discovery import build

    creds = get_google_credencials()
    service = build("gmail", "v1", credentials=creds)

    return _search_gmail(service, query)