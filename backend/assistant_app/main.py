import os
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
import urllib.parse
from dotenv import load_dotenv
import redis
import uuid

from backend.assistant_app.agents.mistral_chat_agent import MistralChatAgent
from backend.assistant_app.api_integration.oauth_client import exchange_code_for_token
from backend.assistant_app.api_integration.token_store import save_token

load_dotenv()

SESSION_ID = os.getenv("SESSION_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
MARKTPLAATS_CLIENT_ID = os.getenv("MARKTPLAATS_CLIENT_ID")
api_name = "marktplaats"
SCOPE = ""

app = FastAPI()
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
    print({"status": "success", "user_id": user_id})

    return {"status": "success", "user_id": user_id}

def __main__():
    with open('backend/assistant-app/configs/chat_config.json') as f:
        config = json.load(f)
    
    chat_agent = MistralChatAgent(config=config)

    while True:
        user_input = input("Chat: ")
        if user_input == "exit":
            break

        content = chat_agent.run(input_data=user_input, session_id=SESSION_ID)

        print(content)


if __name__ == "__main__":
    __main__()