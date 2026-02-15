# LLM Interaction Layer

## Location
`ppBackend/llm/`

## Components

### `models.py` — Data contracts
```python
class LLMProvider(str, Enum):    # gemini, openai, anthropic
class ModelSettings(BaseModel):   # temperature, top_p, top_k, max_tokens
class TokenUsage(BaseModel):      # prompt_tokens, completion_tokens, total_tokens
class GenerateResponse(BaseModel): # content, model, usage
```

### `llm_client.py` — Core wrapper

**`configure_api_keys()`**
- Reads from `ppsecrets/getSecrets.py` (which reads env vars)
- Sets `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` as env vars for LiteLLM
- Idempotent — runs once on first `generate()` call

**`generate(model, messages, settings, response_format)`**
- Wraps `litellm.acompletion()` (async)
- `model`: LiteLLM-prefixed string (e.g., `"gemini/gemini-3-flash-preview"`)
- `messages`: OpenAI-format message list
- `response_format`: Optional `{"type": "json_object"}` for structured output
- Returns `GenerateResponse`
- Catches and wraps all errors into `LLMError`

## Model Name Convention

| Provider | Prefix | Example |
|----------|--------|---------|
| Gemini | `gemini/` | `gemini/gemini-3-flash-preview` |
| OpenAI | `openai/` | `openai/gpt-4o` |
| Anthropic | `anthropic/` | `anthropic/claude-sonnet-4-20250514` |

The `_resolve_model()` helper in `route.py` auto-prefixes bare model names sent by the frontend.
