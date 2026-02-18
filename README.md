# PromptProp: AI-Driven Prompt Refinement

PromptProp is a prompt engineering platform that applies "back-propagation" concepts to natural language instructions. It iteratively optimizes a prompt against a Ground Truth dataset using an ensemble of AI judges to maximize quality and alignment.

## Architecture

```
ppFrontend/          React + Vite + TypeScript
  App.tsx            Optimization loop orchestrator
  services/
    apiService.ts    fetch()-based API client
  components/
    DatasetTable     Ground truth editor + CSV import
    IterationChart   Recharts score progression

ppBackend/           FastAPI + Python
  route.py           API endpoints (inference, jury, refine, metrics, dataset, models)
  optimize.py        Server-side optimization loop with SSE streaming
  models_list.py     Dynamic model discovery across providers
  llm/
    llm_client.py    LiteLLM wrapper — unified generate() for all providers
    models.py        Pydantic models (ModelSettings, GenerateResponse, etc.)
  db/
    models.py        SQLAlchemy ORM (Experiment, DatasetRow, PromptVersion, etc.)
    session.py       Engine + session management (SQLite dev / Postgres prod)
  ppsecrets/         API key management (env vars)
  prompts/           Role definitions (manager, jury, rewriter)
  resources/
    generateMetrics.py   Traditional + non-traditional metric computation
    registerMetrics.py   MLflow experiment tracking integration
  tests/             pytest suite (unit, integration, regression)
```

## Current Status

### Done
- **LLM Interaction Layer** — Generic `generate()` function via LiteLLM supporting Gemini, OpenAI, and Anthropic
- **Backend API Endpoints** — 11 endpoints: inference, jury, refine, metrics, dataset CRUD, model discovery, optimization loop
- **Server-Side Optimization Loop** — Full inference → jury → refine cycle with SSE streaming (`optimize.py`)
- **Multi-Provider Model Discovery** — Dynamic model fetching from Gemini, OpenAI, and Anthropic APIs (`models_list.py`)
- **SQLAlchemy Database Layer** — 6 ORM models (Experiment, DatasetRow, JuryMember, PromptVersion, IterationResult, JuryEvaluation) with cascade relationships
- **Role Prompt Integration** — Manager, Jury, and Rewriter prompts loaded from `.prompt` files and used in endpoints
- **Metric Computation Pipeline** — Traditional (accuracy, precision, recall) and non-traditional (directness, format adherence, consistency, relevance) metrics
- **MLflow Tracking** — Per-iteration metrics logging with prompt versions as artifacts
- **Dataset Management** — Upload, auto-split (train/val/test), and retrieval endpoints
- **Frontend Migration** — React app with fetch-based API client, multi-provider model selector, token usage monitor
- **Test Suite** — 146 pytest tests (unit + integration + regression) with 91% coverage

### In Progress
- IndexedDB for client-side persistence
- Prompt diff view between iterations
- Few-shot example injection
- Synthetic data generation
- Human-in-the-loop annotation
- Advanced convergence strategies

## Tech Stack

| Layer | Technology | Status |
|-------|-----------|--------|
| Frontend | React 19, TypeScript, Vite, Recharts, Tailwind CSS | Active |
| Backend | FastAPI, Uvicorn, Python 3.10+ | Active |
| LLM | LiteLLM (Gemini, OpenAI, Anthropic) | Active |
| Database | SQLAlchemy + SQLite (dev) / PostgreSQL (prod) | Active |
| Tracking | MLflow | Active |
| Testing | pytest, pytest-asyncio, pytest-cov | Active |

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- API key for at least one provider (set as `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` env var)

### Backend
```bash
cd ppBackend
pip install -r ../requirements.txt
python main.py
# Runs on http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Frontend
```bash
cd ppFrontend
npm install
npm run dev
# Runs on http://localhost:3000, proxies /api to backend
```

### Tests
```bash
cd ppBackend
pip install -r requirements-test.txt
pytest tests/ -v
# With coverage:
pytest tests/ --cov=. --cov-report=term-missing
```

### Usage
1. Open `http://localhost:3000`
2. Enter a task description (e.g., "Categorize customer feedback into Product, Billing, Shipping, or General")
3. Add test cases to the Ground Truth table (or import CSV)
4. Configure the jury panel (model + temperature)
5. Click **Propagate Lift** — the system iterates up to 5 cycles, refining the prompt each time

## How It Works

```
Cycle 1..N (max 5):
  1. INFERENCE  — Run current prompt on every test case via selected model
  2. JURY       — Each jury member scores the output (0-100) against expected answer
  3. CONVERGE?  — Stop if avg score >= 98% or score delta < 0.2
  4. REFINE     — Collect failures (score < 90), feed to meta-optimizer
                  which rewrites the prompt targeting specific weaknesses
  5. Loop with new prompt
```
