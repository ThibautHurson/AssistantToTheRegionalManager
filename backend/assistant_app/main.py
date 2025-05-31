import os
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import redis
import uuid
from api_integration.google_token_store import get_google_credencials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


from api.v1.endpoints import tool_router
from agents.mistral_chat_agent import MistralChatAgent
from api_integration.oauth_client import exchange_code_for_token
from api_integration.token_store import save_token


load_dotenv()

SESSION_ID = os.getenv("SESSION_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
MARKTPLAATS_CLIENT_ID = os.getenv("MARKTPLAATS_CLIENT_ID")
api_name = "marktplaats"
SCOPE = ""

app = FastAPI()

app.include_router(tool_router.router)

r = redis.Redis(host="localhost", port=6379, db=0)

@app.get("/login")
async def login(user_id: str):
    # Generate and store a state with the user id during the auth URL generation
    # This ensures you can securely associate the code with the correct user/session.
    state = str(uuid.uuid4())
    r.setex(f"state:{state}", 600, user_id)  # 10-minute expiration

    query_params = {
        "client_id": MARKTPLAATS_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": state
    }
    url = f"https://auth.marktplaats.nl/accounts/oauth/authorize?{urllib.parse.urlencode(query_params)}"
    return RedirectResponse(url)

# Step 2: marktplaats redirects to this endpoint with ?code=
@app.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    # Fetch user context from Redis
    user_id = r.get(f"state:{state}")

    if not code or not user_id:
        raise HTTPException(status_code=400, detail="Missing code or user_id")

    user_id = user_id.decode()

    token = exchange_code_for_token(code)

    save_token(user_id, api_name, token)

    return {"status": "success", "user_id": user_id}

def __main__():

    try:


        creds = get_google_credencials()
        # Call the Gmail API
        service = build("gmail", "v1", credentials=creds)


        from agents.tools.search_gmail import search_gmail

        messages_payload = search_gmail(service, "after:2025/05/20")
        print(messages_payload)

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")


    # while True:
    #     user_input = input("Chat: ")
    #     if user_input == "exit":
    #         break

    #     content = chat_agent.run(input_data=user_input, session_id=SESSION_ID)

    #     print(content)


if __name__ == "__main__":
    __main__()