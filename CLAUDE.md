# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (ppBackend/)
```bash
cd ppBackend && python main.py          # Start FastAPI server on :8000 (Swagger: /docs)
pip install -r requirements.txt         # Install Python deps (from project root)
```

### Frontend (ppFrontend/)
```bash
cd ppFrontend && npm install && npm run dev   # Start Vite dev server on :3000
npm run build                                 # Production build
```

### Environment
Set `ppENV=dev` (default) or `ppENV=prod` to switch config profiles (`ppBackend/configs/*.yaml`).
At least one API key env var required: `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`.

## Architecture

PromptProp is an iterative prompt optimizer ("back-propagation for prompts"). It runs a loop: generate outputs → jury-score them → refine the prompt from failures → repeat.

### Two-process setup
- **Frontend** (React 19 + Vite + TypeScript): Orchestrates the optimization loop, displays results. Vite proxies `/api` → `localhost:8000`.
- **Backend** (FastAPI + LiteLLM): Stateless API that wraps LLM calls. No database yet — all state lives in React.

### Optimization loop (lives in `ppFrontend/App.tsx`)
```
For iteration 1..5:
  1. INFERENCE — POST /api/inference for each dataset row
  2. JURY — POST /api/jury for each (row × jury member), average scores
  3. CONVERGENCE — stop if avg ≥ 98% or delta < 0.2
  4. REFINEMENT — collect failures (score < 90), POST /api/refine → new prompt
```

### Backend LLM layer (`ppBackend/llm/`)
- `llm_client.py`: `generate()` wraps `litellm.acompletion()`. Accepts any LiteLLM-prefixed model string.
- `models.py`: Pydantic models — `GenerateResponse`, `ModelSettings`, `TokenUsage`, `LLMProvider` enum.
- `_resolve_model()` in `route.py` prefixes bare names (e.g. `"gpt-4o"` → `"openai/gpt-4o"`).
- API keys are read from env vars via `ppsecrets/getSecrets.py` and set once at startup.

### API endpoints (`ppBackend/route.py`)
- `POST /api/inference` — run prompt + query through an LLM
- `POST /api/jury` — evaluate output vs expected (returns score 0-100 + reasoning)
- `POST /api/refine` — meta-optimize prompt from failures (hardcoded gemini-3-pro-preview, temp 0.2)
- Several stub endpoints return 501 (jury, evaluate, train/val/test data)

### Role prompts (`ppBackend/prompts/`)
Three authored `.prompt` files (manager, jury, rewriter) define AI roles but are **not yet integrated** — endpoints use hardcoded prompt logic. `getPrompt.py` has incorrect file paths and needs fixing.

### Metrics (`ppBackend/resources/`)
- `registerMetrics.py`: Working MLflow `register()` function, but nothing calls it yet.
- `generateMetrics.py`: Stub — needs traditional (accuracy, precision, recall) and custom metrics.

## Key conventions
- Backend uses async FastAPI with Pydantic request/response models
- LLM calls always go through `generate()` in `llm_client.py`, never direct SDK calls
- Model names must be LiteLLM-prefixed (`gemini/...`, `openai/...`, `anthropic/...`)
- Frontend uses native `fetch()` via `services/apiService.ts` — no axios
- Config loaded from YAML via `ppENV` env var; secrets from env vars only
- Task board is in `TASKS.md`; detailed docs in `docs/`