import os
from functools import lru_cache

_PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


@lru_cache(maxsize=None)
def get_prompt(name: str) -> str:
    """Load a .prompt file by name (e.g. 'jury', 'rewriter', 'manager').

    Files are read from the same directory as this module and cached
    permanently for the lifetime of the process.
    """
    path = os.path.join(_PROMPTS_DIR, f"{name}.prompt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
