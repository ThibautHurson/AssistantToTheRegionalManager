import base64
import json
from email.mime.text import MIMEText
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from backend.assistant_app.utils.handle_errors import retry_on_rate_limit_async
from backend.assistant_app.api_integration.google_token_store import load_credentials

MAX_RESULTS = 10


@retry_on_rate_limit_async(
    max_attempts=3,
    wait_seconds=2,
    retry_on_status=[429, 500, 502, 503, 504],
    return_none_on_404=True,
)
async def get_gmail(service, message_id):
    """
    Get Gmail message content with retry logic, and return payload, history_id, and labels.
    """
    msg_data = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    payload = msg_data["payload"]
    history_id = msg_data["historyId"]
    labels = msg_data.get("labelIds", [])

    def get_parts(part):
        if "parts" in part:
            for sub_part in part["parts"]:
                yield from get_parts(sub_part)
        elif part.get("mimeType") == "text/plain" and "data" in part["body"]:
            yield base64.urlsafe_b64decode(part["body"]["data"]).decode()

    return "\n".join(get_parts(payload)), history_id, labels


@retry_on_rate_limit_async(
    max_attempts=3,
    wait_seconds=2,
    retry_on_status=[429, 500, 502, 503, 504],
    return_none_on_404=True,
)
async def _search_gmail(service, query: str):
    """
    Search Gmail with retry logic.
    """
    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=MAX_RESULTS)
        .execute()
    )
    messages = results.get("messages", [])
    messages_payload = []

    for msg in messages[:MAX_RESULTS]:
        content, _, _ = await get_gmail(service, msg["id"])
        if content:
            messages_payload.append(
                {
                    "content": content,
                    "message_id": msg["id"],
                    "gmail_link": f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
                }
            )
    return json.dumps(messages_payload)


async def search_gmail(query: str, user_email: str):
    """
    Search Gmail messages with retry logic.
    """
    creds = load_credentials(user_email)
    service = build("gmail", "v1", credentials=creds)

    return await _search_gmail(service, query)


async def send_gmail(to: str, subject: str, body: str, user_email: str):
    """
    Send an email using Gmail.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text)
    """
    creds = load_credentials(user_email)
    service = build("gmail", "v1", credentials=creds)

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    message_body = {"raw": raw}
    sent_message = (
        service.users().messages().send(userId="me", body=message_body).execute()
    )
    return (
        f"Email sent to {to} with subject '{subject}'. View: "
        f"https://mail.google.com/mail/u/0/#inbox/{sent_message.get('id')}"
    )


async def reply_to_gmail(message_id: str, body: str, user_email: str):
    """
    Reply to an email using Gmail.

    Args:
        message_id: The ID of the message to reply to
        body: The reply body (plain text)
    """
    if not message_id or len(message_id) < 10:
        # Gmail message IDs are long hex strings
        return (
            f"Invalid message_id: '{message_id}'. Please provide a valid Gmail message ID."
        )

    creds = load_credentials(user_email)
    service = build("gmail", "v1", credentials=creds)

    try:
        # Get the original message to extract headers
        original = service.users().messages().get(
            userId='me',
            id=message_id,
            format='metadata',
            metadataHeaders=['Subject', 'From', 'To', 'Message-ID']
        ).execute()
    except HttpError as e:
        if hasattr(e, "resp") and getattr(e.resp, "status", None) == 404:
            return (
                f"Could not find the email with ID {message_id}. "
                "It may have been deleted or is not accessible."
            )
        raise

    headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}
    subject = headers.get("Subject", "")
    to = headers.get("From", "")

    # Prepare reply headers
    reply = MIMEText(body)
    reply["to"] = to
    reply["subject"] = (
        "Re: " + subject if not subject.lower().startswith("re:") else subject
    )
    if "Message-ID" in headers:
        reply["In-Reply-To"] = headers["Message-ID"]
        reply["References"] = headers["Message-ID"]

    raw = base64.urlsafe_b64encode(reply.as_bytes()).decode()
    message_body = {
        "raw": raw,
        "threadId": original.get("threadId"),
    }
    sent_message = (
        service.users().messages().send(userId="me", body=message_body).execute()
    )
    return (
        f"Reply sent to {to}. View: "
        f"https://mail.google.com/mail/u/0/#inbox/{sent_message.get('id')}"
    )
