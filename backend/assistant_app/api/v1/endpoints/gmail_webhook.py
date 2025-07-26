import base64
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from googleapiclient.discovery import build

from backend.assistant_app.agents.tools.gmail_tools import get_gmail
from backend.assistant_app.api_integration.google_token_store import load_credentials
from backend.assistant_app.utils.redis_saver import load_from_redis, save_to_redis

from backend.assistant_app.services.task_detector import TaskDetector
from backend.assistant_app.models.task_manager import TaskManager
from backend.assistant_app.models.task import Task as TaskModel
from backend.assistant_app.api_integration.db import get_db
from backend.assistant_app.utils.logger import webhook_logger, error_logger

load_dotenv()
router = APIRouter()

HISTORY_KEY = "historyId"

task_detector = TaskDetector()

MAX_CONCURRENT_TASKS = 3
RATE_LIMIT_DELAY = 1
MAX_NOTIFICATION_AGE = 60 * 60 * 10  # Skip notifications older than 10 hours


def is_notification_too_old(publish_time: str) -> bool:
    """Check if the notification is too old to process"""
    try:
        publish_dt = datetime.fromisoformat(publish_time.replace('Z', '+00:00'))
        age = datetime.now(publish_dt.tzinfo) - publish_dt
        return age.total_seconds() > MAX_NOTIFICATION_AGE
    except Exception as e:
        error_logger.log_error(e, {"context": "parse_publish_time", "publish_time": publish_time})
        return True  # If we can't parse the time, skip it

@router.post("/gmail/push")
async def gmail_webhook(request: Request):
    data = await request.json()
    webhook_logger.log_info("Webhook received", {"data": data})
    message = data.get("message", {})
    message_data = message.get("data")

    if not message_data:
        return JSONResponse({"error": "No message data received"}, status_code=400)

    try:
        decoded = json.loads(base64.b64decode(message_data).decode("utf-8"))
        email_address = decoded["emailAddress"]
        webhook_logger.log_info("New email notification", {"email_address": email_address})
        history_id = str(decoded["historyId"])
        publish_time = message.get("publishTime") or message.get("publish_time")

        # Skip old notifications
        if is_notification_too_old(publish_time):
            webhook_logger.log_info("Skipping old notification", {"publish_time": publish_time})
            return {"status": "skipped", "reason": "notification_too_old"}

    except Exception as e:
        error_logger.log_error(e, {"context": "decode_message_data"})
        return JSONResponse({"error": "Invalid message data"}, status_code=400)

    """
    Because Gmail Pub/Sub push notifications are eventual and incremental, and the startHistoryId
    you get from the webhook often does not contain the new message yet, we fetch the previous historyId
    from redis memory
    """
    webhook_logger.log_debug("Loading history ID from Redis", {"email_address": email_address})
    start_history_id = load_from_redis(email_address, HISTORY_KEY)
    webhook_logger.log_debug("Loaded history ID", {"start_history_id": start_history_id})

    if not start_history_id:
        start_history_id = str(int(history_id) - 10)  # fallback for first-time

    elif start_history_id and (history_id < start_history_id):
        webhook_logger.log_info("Skipping notification - history ID too old", {
            "history_id": history_id,
            "start_history_id": start_history_id
        })
        return {"status": "skipped", "reason": "history_id_too_old"}

    # Update historyId in redis
    save_to_redis(email_address, HISTORY_KEY, history_id)

    webhook_logger.log_debug("Loading credentials", {"email_address": email_address})
    creds = load_credentials(email_address)
    if not creds:
        webhook_logger.log_warning("No credentials found", {"email_address": email_address})
        return JSONResponse({"error": "User not authenticated"}, status_code=401)

    webhook_logger.log_info("Credentials loaded successfully", {"email_address": email_address})
    service = build("gmail", "v1", credentials=creds)

    # Fetch history since history_id to get new messages
    try:
        history_response = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            historyTypes=['messageAdded']
        ).execute()
    except Exception as e:
        error_logger.log_error(e, {"context": "fetch_history", "email_address": email_address})
        return JSONResponse({"error": str(e)}, status_code=500)

    messages = []
    if "history" in history_response:
        for record in history_response["history"]:
            if "messagesAdded" in record:
                for msg in record["messagesAdded"]:
                    msg_id = msg["message"]["id"]
                    messages.append(msg_id)
    webhook_logger.log_info("Number of messages", {"count": len(messages)})

    if not messages:
        webhook_logger.log_info("No new messages to process")
        return JSONResponse({"status": "ok", "messages_fetched": 0, "tasks_created": []},
                            status_code=200)

    results = []
    tasks_created = []
    task_manager = TaskManager(email_address)  # Using email as session_id

    newest_history_id = history_id
    # Process messages in batches to respect rate limits
    for i in range(0, len(messages), MAX_CONCURRENT_TASKS):
        batch = messages[i:i + MAX_CONCURRENT_TASKS]

        # A queue to hold message data and its corresponding task detection coroutine
        processing_queue = []

        for msg_id in batch:
            try:
                db = next(get_db())
                try:
                    # Deduplication check
                    existing_task = db.query(TaskModel).filter_by(gmail_message_id=msg_id).first()
                    if existing_task:
                        webhook_logger.log_info("Task already exists, skipping", {"msg_id": msg_id})
                        continue
                finally:
                    db.close()

                # Properly await the get_gmail call
                msg_data, msg_history_id, labels = await get_gmail(service, msg_id)
                if "INBOX" not in labels:
                    webhook_logger.log_info("Skipping message - not in INBOX", {
                        "msg_id": msg_id,
                        "labels": labels,
                        "email_address": email_address
                    })
                    continue
                newest_history_id = max(newest_history_id, msg_history_id)
                if not msg_data:
                    webhook_logger.log_warning("No content received", {"msg_id": msg_id})
                    continue

                # Add message data and the task detection coroutine to the queue
                processing_queue.append({
                    "msg_id": msg_id,
                    "msg_data": msg_data,
                    "task_coro": task_detector.process_email(
                        email_content=msg_data,
                        email_subject=None
                    )
                })
                results.append(msg_data) # Keep for original counting logic

            except Exception as e:
                error_logger.log_error(e, {"context": "fetch_message", "msg_id": msg_id})
                continue

        # Process batch of tasks if any messages are in the queue
        if processing_queue:
            task_coroutines = [item['task_coro'] for item in processing_queue]
            try:
                task_results = await asyncio.gather(*task_coroutines, return_exceptions=True)

                for i, item in enumerate(processing_queue):
                    task_details = task_results[i]
                    if isinstance(task_details, Exception):
                        error_logger.log_error(task_details, {
                            "context": "task_detection",
                            "msg_id": item['msg_id'],
                            "email_address": email_address
                        })
                        continue

                    if task_details:
                        webhook_logger.log_info("Task detected in email", {
                            "title": task_details.get('title', 'Untitled Task'),
                            "email_address": email_address
                        })
                        try:
                            # Use the correct msg_id and msg_data from the item in the queue
                            task = task_manager.add_task(
                                title=task_details.get("title", "Task from email"),
                                description=task_details.get("description",
                                                             item['msg_data'][:200] + "..."),
                                due_date=task_details.get("due_date"),
                                priority=task_details.get("priority", 1),
                                msg_id=item['msg_id']
                            )
                            tasks_created.append(task.ticket_id)
                            webhook_logger.log_info("Created task", {"task_id": task.ticket_id})
                        except Exception as e:
                            error_logger.log_error(e, {"context": "create_task", "msg_id": item['msg_id']})
            except Exception as e:
                error_logger.log_error(e, {"context": "process_batch"})

        # Add delay between batches to respect rate limits
        if i + MAX_CONCURRENT_TASKS < len(messages):
            await asyncio.sleep(RATE_LIMIT_DELAY)

    webhook_logger.log_info("Newest history ID", {"newest_history_id": newest_history_id})
    # Update historyId in redis with the newest historyId from the messages
    save_to_redis(email_address, HISTORY_KEY, newest_history_id)

    webhook_logger.log_info("Processing completed", {
        "messages_fetched": len(results),
        "tasks_created": tasks_created,
        "email_address": email_address
    })

    return JSONResponse({
        "status": "ok",
        "messages_fetched": len(results),
        "tasks_created": tasks_created
    }, status_code=200)
