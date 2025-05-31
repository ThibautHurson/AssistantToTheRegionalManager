from pathlib import Path

PROMPT_DIR = Path(__file__).parent

def load_prompt(name: str) -> str:
    """Load a tool/system prompt from a .md file."""
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {name}.md")
    return path.read_text(encoding="utf-8")