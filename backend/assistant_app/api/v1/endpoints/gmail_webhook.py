from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import base64
from dotenv import load_dotenv
import os
import json
from googleapiclient.discovery import build

from backend.assistant_app.agents.tools.gmail_tools import get_gmail
from backend.assistant_app.api_integration.google_token_store import load_credentials
from backend.assistant_app.utils.redis_saver import load_from_redis, save_to_redis

load_dotenv()
router = APIRouter()

HISTORY_KEY = "historyId"

@router.post("/gmail/push")
async def gmail_webhook(request: Request):
    data = await request.json()
    print("Webhook received data:", data)
    message = data.get("message", {})  
    message_data = message.get("data")

    if message_data:
        decoded = json.loads(base64.b64decode(message_data).decode("utf-8"))
        email_address = decoded["emailAddress"]
        print("New email notification for:", email_address)
        history_id = decoded["historyId"]

    """
    Because Gmail Pub/Sub push notifications are eventual and incremental, and the startHistoryId 
    you get from the webhook often does not contain the new message yet, we fetch the previous historyId
    from redis memory
    """
    print(f"Loading history ID from Redis for email: {email_address}")
    start_history_id = load_from_redis(email_address, HISTORY_KEY)
    print(f"Loaded history ID: {start_history_id}")
    
    # Update historId in redis
    save_to_redis(email_address, HISTORY_KEY, history_id)
    if not start_history_id:
        start_history_id = str(int(history_id) - 10)  # fallback for first-time

    print(f"Loading credentials for email: {email_address}")
    creds = load_credentials(email_address)
    if not creds:
        print(f"No credentials found in Redis for email: {email_address}")
        return JSONResponse({"error": "User not authenticated"}, status_code=401)
    
    print("Credentials loaded successfully")
    service = build("gmail", "v1", credentials=creds)

    # Fetch history since history_id to get new messages
    try:
        history_response = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            historyTypes=['messageAdded']
        ).execute()
    except Exception as e:
        print("Error fetching history:", e)
        return {"status": "error", "detail": str(e)}

    messages = []
    if "history" in history_response:
        for record in history_response["history"]:
            if "messagesAdded" in record:
                for msg in record["messagesAdded"]:
                    msg_id = msg["message"]["id"]
                    messages.append(msg_id)
    print("Number of messages:", len(messages))
    
    results = []
    for msg_id in messages:
        try:
            msg_data = get_gmail(service, msg_id)
            results.append(msg_data)
        except Exception as e:
            print(f"Error fetching message {msg_id}: {e}")

    print(f"Fetched {len(results)} messages.")
    print(results)

    return {"status": "ok", "messages_fetched": len(results)}