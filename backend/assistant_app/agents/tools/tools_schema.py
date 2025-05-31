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
    }
]
