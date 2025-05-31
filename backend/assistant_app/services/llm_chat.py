from agents.mistral_chat_agent import MistralChatAgent
import json

def chat_with_llm(prompt: str, session_id: str) -> str:

    with open('backend/assistant_app/configs/chat_config.json') as f:
        config = json.load(f)
    
    chat_agent = MistralChatAgent(config=config)
    return chat_agent.run(input_data=prompt, session_id=session_id)