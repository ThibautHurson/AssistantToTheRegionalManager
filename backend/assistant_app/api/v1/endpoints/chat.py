from fastapi import APIRouter, ChatRequest
from assistant_app.services.llm_chat import chat_with_llm

router = APIRouter()

@router.post("/chat")
async def chat(payload: ChatRequest):
    return {"response": chat_with_llm(payload.prompt, payload.session_id)}