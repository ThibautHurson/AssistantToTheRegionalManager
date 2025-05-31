from dotenv import load_dotenv
import os
import httpx
import json
from utils.handle_errors import handle_httpx_errors
import base64
from utils.tool_registry import register_tool

load_dotenv()

@register_tool
def search_gmail(service, query):
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    print(f"Found {len(messages)} message(s)")
    messages_payload = []
    for msg in messages[:2]:  # Show only the first 5 for now
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        
        payload = msg_data['payload']

        def get_parts(part):
            if 'parts' in part:
                for sub_part in part['parts']:
                    yield from get_parts(sub_part)
            elif part.get('mimeType') == 'text/plain' and 'data' in part['body']:
                yield base64.urlsafe_b64decode(part['body']['data']).decode()

        messages_payload.append("\n".join(get_parts(payload)))        # snippet = msg_data.get("snippet", "")
    return messages_payload
