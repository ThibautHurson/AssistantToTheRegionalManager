tool_registry = {}

def register_tool(func=None, *, name=None):
    def decorator(f):
        tool_name = name or f.__name__
        print(f"Registering tool: {tool_name}")
        tool_registry[tool_name] = f
        return f

    # Case: used as @register_tool
    if func is not None:
        return decorator(func)

    # Case: used as @register_tool(name="...") → returns actual decorator
    return decorator