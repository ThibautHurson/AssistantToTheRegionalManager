tool_registry = {}

def register_tool(name=None):
    """
    Decorator used to register tools
    """
    def decorator(func):
        tool_name = name or func.__name__
        tool_registry[tool_name] = func
        return func
    return decorator