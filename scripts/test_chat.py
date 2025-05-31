import json
from dotenv import load_dotenv
import os
from backend.assistant_app.agents.mistral_chat_agent import MistralChatAgent
import backend.assistant_app.agents.tools  # this triggers registration
from backend.assistant_app.utils.tool_registry import tool_registry
from backend.assistant_app.agents.prompts.prompt_builder import build_system_prompt
from backend.assistant_app.agents.tools.tools_schema import tools_schema

load_dotenv()

SESSION_ID = os.getenv("SESSION_ID")

def test_chat():
    tools = tool_registry.keys()
    print("Tool registry", tools)
    system_prompt = build_system_prompt(tools)
    

    with open("backend/assistant_app/configs/chat_config.json") as f:
        config = json.load(f)

    chat_agent = MistralChatAgent(config=config, 
                                  system_prompt=system_prompt,
                                  tools=tools_schema)

    while True:
        user_input = input("Chat: ")
        if user_input == "exit":
            break

        content = chat_agent.run(input_data=user_input, session_id=SESSION_ID)

        print(content)


if __name__ == "__main__":
    test_chat()