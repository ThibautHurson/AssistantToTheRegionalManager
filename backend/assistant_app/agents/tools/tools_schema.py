tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "search_gmail",
            "description": "Search gmail based on a query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail-compatible search query"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Add a new task to the task manager",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the task"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the task"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Optional due date for the task in ISO format"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Task priority (1-5, default 1)"
                    }
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "Delete a task from the task manager",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to delete"
                    }
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Update a task in the task manager",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title for the task"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description for the task"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "New due date in ISO format"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "New priority (1-5)"
                    },
                    "status": {
                        "type": "string",
                        "description": "New status (pending, in_progress, completed)"
                    }
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List all tasks for the user, optionally filtered by status and priority",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Optional status filter (pending, in_progress, completed). Do not use this unless the user asks for it."
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Optional priority filter (1-5)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_task",
            "description": "Get the next task based on priority and due date",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_gmail",
            "description": "Send an email using Gmail. ALWAYS validate with the user that the recipient, subject, and body of the email are correct before sending it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "The email address of the recipient"
                    },
                    "subject": {
                        "type": "string",
                        "description": "The subject of the email"
                    },
                    "body": {
                        "type": "string",
                        "description": "The body of the email"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reply_to_gmail",
            "description": "Reply to an email using Gmail. ALWAYS validate with the user that the recipient, subject, and body of the email are correct before sending it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The ID of the message to reply to"
                    },
                    "body": {
                        "type": "string",
                        "description": "The body of the reply"
                    }
                },
                "required": ["message_id", "body"]
            }
        }
    }
]
