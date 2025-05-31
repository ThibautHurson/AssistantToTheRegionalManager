from . import load_prompt

def build_system_prompt(tools: list[str], base_prompt: str = "default_system_prompt") -> str:
    """
    Build the system prompt with instructions for all active tools.
    
    Args:
        tools: List of tool names, e.g., ["gmail_search", "calendar_lookup"]
        base_prompt: Filename for the base system prompt (default: default_system_prompt.md)
        
    Returns:
        A single string that combines the base system prompt and tool instructions.
    """
    prompt_sections = [load_prompt(base_prompt)]
    
    for tool in tools:
        try:
            section = load_prompt(f"{tool}_prompt")
            prompt_sections.append(f"\n### Instructions for `{tool}`\n{section}")
        except FileNotFoundError:
            print(f"[Warning] No prompt found for tool: {tool}")
    
    return "\n\n".join(prompt_sections)