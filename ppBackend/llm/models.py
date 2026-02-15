from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers. Values match LiteLLM model prefixes."""
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ModelSettings(BaseModel):
    """Generation parameters. Mirrors frontend ModelSettings interface."""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    max_tokens: Optional[int] = Field(default=None, ge=1)


class TokenUsage(BaseModel):
    """Token consumption metadata."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GenerateResponse(BaseModel):
    """Output from the generate() function."""
    content: str
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)