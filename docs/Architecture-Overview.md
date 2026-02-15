# Architecture Overview

## System Diagram

```
┌─────────────────────────────────┐     ┌──────────────────────────────────┐
│         ppFrontend              │     │          ppBackend               │
│  (React + Vite + TypeScript)    │     │     (FastAPI + Python)           │
│                                 │     │                                  │
│  App.tsx                        │     │  route.py                        │
│    ├─ Optimization loop         │────▶│    ├─ POST /api/inference        │
│    ├─ State management          │     │    ├─ POST /api/jury             │
│    └─ UI rendering              │◀────│    └─ POST /api/refine           │
│                                 │     │                                  │
│  services/apiService.ts         │     │  llm/llm_client.py              │
│    └─ fetch() to /api/*         │     │    └─ generate() via LiteLLM    │
│                                 │     │                                  │
│  components/                    │     │  prompts/*.prompt                │
│    ├─ DatasetTable.tsx          │     │    ├─ manager.prompt             │
│    └─ IterationChart.tsx        │     │    ├─ jury.prompt                │
│                                 │     │    └─ rewriter.prompt            │
│  Port 3000                      │     │                                  │
│  (Vite proxies /api → :8000)   │     │  Port 8000                       │
└─────────────────────────────────┘     └──────────────────────────────────┘
                                                      │
                                        ┌─────────────┴─────────────┐
                                        │     LLM Providers         │
                                        │  ┌─────────┐ ┌─────────┐ │
                                        │  │ Gemini  │ │ OpenAI  │ │
                                        │  └─────────┘ └─────────┘ │
                                        │  ┌───────────┐           │
                                        │  │ Anthropic │           │
                                        │  └───────────┘           │
                                        └───────────────────────────┘
```

## Data Flow

1. User configures task, dataset, jury panel in the frontend
2. Frontend orchestrates the optimization loop, calling backend per-step
3. Backend routes receive requests, call `llm.generate()` via LiteLLM
4. LiteLLM routes to the appropriate provider (Gemini/OpenAI/Anthropic)
5. Results flow back through the chain to the UI

## Key Design Decisions

- **Frontend-driven loop**: The optimization loop runs in the browser for now. This keeps the backend stateless and simple. A future milestone moves it server-side.
- **LiteLLM abstraction**: All LLM calls go through a single `generate()` function. Switching providers requires only changing the model string prefix.
- **Structured JSON output**: Jury and refinement endpoints request `response_format: json_object` so responses are parseable.
