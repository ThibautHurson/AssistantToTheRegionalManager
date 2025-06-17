from typing import Optional, Dict, Any
from datetime import datetime
import re
from mistralai import Mistral
from mistralai.models import sdkerror
import os
from dotenv import load_dotenv
import json
from backend.assistant_app.utils.handle_errors import retry_on_rate_limit_async

load_dotenv()

class TaskDetector:
    def __init__(self):
        api_key = os.getenv("MISTRAL_KEY")
        if not api_key:
            raise ValueError("MISTRAL_KEY environment variable is not set")
        self.client = Mistral(api_key=api_key)
        self.model = "mistral-small-latest"

    @retry_on_rate_limit_async(
        max_attempts=5,
        wait_seconds=1,
        retry_on=sdkerror.SDKError
    )
    async def _is_task_relevant(self, content: str) -> bool:
        """Use Mistral to determine if the email content contains a relevant task."""
        prompt = f"""Analyze this email content and determine if it contains a relevant task that needs to be tracked.
        A relevant task should be:
        1. Actionable (has a clear action to take)
        2. Important (E.g Taxes, Bills, Recruitment, etc.). Do NOT include ads, newsletters, etc.
        
        Email content:
        {content}
        """
        
        response = await self.client.chat.complete_async(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "Task Relevance",
                        "schema_definition": {
                            "type": "object",
                            "properties": {
                                "is_relevant": {
                                    "type": "boolean",
                                    "description": "Whether the email content contains a relevant task"
                                }
                            },
                            "required": ["is_relevant"]
                        }
                    }
                }
        )
        
        return json.loads(response.choices[0].message.content)["is_relevant"]
    
    @retry_on_rate_limit_async(
        max_attempts=5,
        wait_seconds=1,
        retry_on=sdkerror.SDKError
    )
    async def _extract_task_details(self, content: str) -> Dict[str, Any]:
        """Extract task details from email content using Mistral."""
        prompt = f"""Extract task details from this email content.
        Email content:
        {content}
        
        Return only the JSON object, nothing else."""
        
        response = await self.client.chat.complete_async(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "Task Relevance",
                    "schema_definition": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "A clear, concise title for the task"
                            },
                            "description": {
                                "type": "string",
                                "description": "The full task description"
                            },
                            "due_date": {
                                "type": "string",
                                "description": "The due date of the task in ISO format date"
                            },
                            "priority": {
                                "type": "integer",
                                "description": "The priority of the task.  0 (high), 1 (medium), 2 (low), or 3 (lowest). If no due date is mentioned, set the priority to 1."
                            }
                        },
                        "required": ["title", "description", "priority"]
                    }
                }
            }
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except:
            return {
                "title": "Task from email",
                "description": content[:200] + "...",
                "due_date": None,
                "priority": 1
            }

    async def process_email(self, email_content: str, email_subject: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Process an email and return task details if relevant."""
        full_content = f"Subject: {email_subject}\n\n{email_content}" if email_subject else email_content
        
        if await self._is_task_relevant(full_content):
            task_details = await self._extract_task_details(full_content)
            return task_details
        
        return None