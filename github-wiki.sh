#!/bin/bash
# Creates GitHub wiki pages for PromptProp.
# Run from repo root after installing gh CLI.
# Note: Wiki must be enabled on the repo first (Settings → Features → Wikis).
# Usage: bash github-wiki.sh

set -e

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
WIKI_REPO="https://github.com/${REPO}.wiki.git"

# Clone wiki repo
TMPDIR=$(mktemp -d)
git clone "$WIKI_REPO" "$TMPDIR" 2>/dev/null || {
  echo "Wiki not initialized. Creating first page via API..."
  # Create Home page to initialize the wiki
  mkdir -p "$TMPDIR"
  cd "$TMPDIR"
  git init
  git remote add origin "$WIKI_REPO"
}

cd "$TMPDIR"

# ===========================================================================
# Home
# ===========================================================================
cat > Home.md <<'EOF'
# PromptProp Wiki

Welcome to the PromptProp wiki — the technical reference for the AI-Driven Prompt Refinement platform.

## Pages

- [[Architecture Overview]] — System design, component diagram, data flow
- [[LLM Interaction Layer]] — How the LiteLLM wrapper works
- [[API Reference]] — Backend endpoint documentation
- [[Optimization Loop]] — How back-propagation works on prompts
- [[Role System]] — Manager, Jury, and Rewriter prompt roles
- [[Frontend Guide]] — React app structure and component overview
- [[Development Setup]] — Getting started for contributors
EOF

# ===========================================================================
# Architecture Overview
# ===========================================================================
cat > "Architecture-Overview.md" <<'EOF'
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
EOF

# ===========================================================================
# LLM Interaction Layer
# ===========================================================================
cat > "LLM-Interaction-Layer.md" <<'EOF'
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
- Sets `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` as env vars
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
EOF

# ===========================================================================
# API Reference
# ===========================================================================
cat > "API-Reference.md" <<'EOF'
# API Reference

Base URL: `http://localhost:8000`

## Core Endpoints

### POST /api/inference
Run a prompt against a single test case.

**Request:**
```json
{
  "model": "gemini-3-flash-preview",
  "taskDescription": "Categorize customer feedback",
  "promptTemplate": "You are a classifier...",
  "query": "My package arrived damaged",
  "settings": { "temperature": 0.1, "topP": 0.95, "topK": 40 }
}
```

**Response:**
```json
{ "output": "Category: Shipping\nThe customer reports..." }
```

### POST /api/jury
Evaluate model output using a jury member.

**Request:**
```json
{
  "juryModel": "gemini-3-pro-preview",
  "jurySettings": { "temperature": 0 },
  "taskDescription": "Categorize customer feedback",
  "row": {
    "query": "My package arrived damaged",
    "expectedOutput": "Shipping",
    "softNegatives": "Don't be verbose",
    "hardNegatives": "Never say Billing for shipping issues"
  },
  "actualOutput": "Category: Shipping"
}
```

**Response:**
```json
{ "score": 92.0, "reasoning": "Correctly identified as Shipping..." }
```

### POST /api/refine
Refine a prompt based on failure feedback.

**Request:**
```json
{
  "taskDescription": "Categorize customer feedback",
  "currentPrompt": "You are a classifier...",
  "failures": "Query: ...\nExpected: ...\nActual: ...\nCritique: ..."
}
```

**Response:**
```json
{
  "explanation": "Added explicit category definitions",
  "refinedPrompt": "You are a classifier. Categories are...",
  "deltaReasoning": "Failures showed category confusion..."
}
```

## Utility Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Welcome message |
| `/health-check` | GET | Returns `{"status": "healthy"}` |

## Error Responses
- `502 Bad Gateway` — LLM call failed (auth error, rate limit, bad request)
- `422 Unprocessable Entity` — Invalid request body (Pydantic validation)
EOF

# ===========================================================================
# Optimization Loop
# ===========================================================================
cat > "Optimization-Loop.md" <<'EOF'
# Optimization Loop

## Overview

PromptProp uses an iterative "back-propagation" approach to prompt refinement:

```
Start with: task description + seed prompt + dataset + jury config

FOR iteration = 1 to MAX_ITERATIONS (5):

  1. INFERENCE PHASE
     For each test case in dataset:
       Call POST /api/inference with current prompt + test query
       Collect actual output

  2. JURY EVALUATION PHASE
     For each test case result:
       For each jury member:
         Call POST /api/jury with actual output vs expected output
         Collect score (0-100) and reasoning
       Calculate average score across jury members

  3. CONVERGENCE CHECK
     Calculate iteration average score
     IF average >= 98%  →  STOP (excellence achieved)
     IF |current_avg - previous_avg| < 0.2  →  STOP (plateau detected)

  4. REFINEMENT PHASE
     Collect all failed cases (score < 90)
     Format failures as: query + expected + actual + jury critique
     Call POST /api/refine with current prompt + failures
     Replace current prompt with refined version

  5. LOOP
```

## Key Parameters
- **Max iterations**: 5 (hardcoded in `App.tsx`)
- **Convergence threshold**: 98% average score
- **Plateau detection**: Score change < 0.2 between iterations
- **Failure threshold**: Cases scoring below 90 are sent for refinement
- **Refinement model**: `gemini-3-pro-preview` at temperature 0.2

## Scoring System
- Each jury member independently scores 0-100
- Hard negative violations → score below 40
- Scores are averaged across all jury members per test case
- Iteration score = average of all test case scores
EOF

# ===========================================================================
# Role System
# ===========================================================================
cat > "Role-System.md" <<'EOF'
# Role System

PromptProp defines three AI roles for the optimization pipeline. Role definitions live in `ppBackend/prompts/`.

## Manager (`manager.prompt`)
The orchestrator responsible for:
- Coordinating the full refinement workflow
- Creating train/validation/test data splits
- Designing evaluation features for the jury
- Tracking progress and documenting decisions
- Measuring traditional metrics (accuracy, precision, recall) and non-traditional metrics (directness, format adherence, consistency)

**Status**: Prompt authored, not yet integrated into backend logic.

## Jury (`jury.prompt`)
Evaluators that score LLM outputs:
- Evaluate across Accuracy, Relevance, Completeness (0-10 each)
- Perform bias self-checks using provided evaluation features
- Provide structured feedback with specific evidence
- Adapt evaluation to domain-specific conventions

**Status**: Prompt authored. A simplified version is used inline in `/api/jury`.

## Rewriter (`rewriter.prompt`)
The prompt optimizer that:
- Analyzes jury feedback patterns across all test cases
- Diagnoses root causes (unclear wording, missing constraints, format issues)
- Makes incremental, evidence-based prompt edits
- Tracks version history and predicts metric improvements

**Status**: Prompt authored. A simplified version is used inline in `/api/refine`.
EOF

# ===========================================================================
# Frontend Guide
# ===========================================================================
cat > "Frontend-Guide.md" <<'EOF'
# Frontend Guide

## Location
`ppFrontend/`

## Stack
- React 19 with TypeScript
- Vite 6 (dev server + build)
- Tailwind CSS (via CDN)
- Recharts (score visualization)

## Key Files

### `App.tsx` (~540 lines)
Main component containing:
- `AppState` — all application state (task, prompt, dataset, jury, history)
- `startOptimization()` — the optimization loop
- `addJuryMember()` — jury panel management
- Sidebar (controls) + Main workspace (results)

### `services/apiService.ts`
Three functions that POST to the backend:
- `runInference()` → `/api/inference`
- `evaluateWithJury()` → `/api/jury`
- `refinePrompt()` → `/api/refine`

### `components/DatasetTable.tsx`
- Editable table for ground truth test cases
- CSV import support
- Fields: query, expectedOutput, softNegatives, hardNegatives

### `components/IterationChart.tsx`
- Recharts line graph: iteration number vs average score
- Only renders when 2+ iterations exist

### `types.ts`
TypeScript interfaces matching the backend Pydantic models.

## Dev Proxy
`vite.config.ts` proxies `/api` requests to `http://localhost:8000` so the frontend and backend can run on different ports during development.
EOF

# ===========================================================================
# Development Setup
# ===========================================================================
cat > "Development-Setup.md" <<'EOF'
# Development Setup

## Prerequisites
- Python 3.10+
- Node.js 18+
- Git
- At least one LLM API key

## Clone & Install

```bash
git clone <repo-url>
cd PromptProp

# Backend
cd ppBackend
python -m venv ../.venv
source ../.venv/bin/activate  # or ..\.venv\Scripts\activate on Windows
pip install -r ../requirements.txt

# Frontend
cd ../ppFrontend
npm install
```

## Environment Variables

Set API keys as environment variables:
```bash
export GEMINI_API_KEY=your-key-here
export OPENAI_API_KEY=your-key-here      # optional
export ANTHROPIC_API_KEY=your-key-here   # optional
```

Or create a `.env` file in the project root (it's gitignored).

## Running

Terminal 1 (Backend):
```bash
cd ppBackend
python main.py
# http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

Terminal 2 (Frontend):
```bash
cd ppFrontend
npm run dev
# http://localhost:3000
```

## Project Structure
```
PromptProp/
├── ppBackend/
│   ├── main.py              # Server entry point
│   ├── route.py             # API endpoints
│   ├── llm/                 # LiteLLM wrapper
│   ├── prompts/             # Role definitions
│   ├── ppsecrets/           # API key management
│   ├── configs/             # YAML configs (dev/prod)
│   └── resources/           # MLflow metrics
├── ppFrontend/
│   ├── App.tsx              # Main React component
│   ├── services/            # API client
│   ├── components/          # UI components
│   └── types.ts             # TypeScript types
├── requirements.txt         # Python dependencies
└── README.md
```

## Configuration
- Backend config: `ppBackend/configs/dev.yaml` / `prod.yaml`
- Set environment: `export ppENV=dev` (default) or `export ppENV=prod`
EOF

# Commit and push wiki
git add -A
git commit -m "Add wiki pages" 2>/dev/null || true
git push origin master 2>/dev/null || git push origin main 2>/dev/null || echo "Push failed — you may need to enable wiki on the repo first"

# Cleanup
rm -rf "$TMPDIR"

echo ""
echo "Wiki pages created successfully!"
