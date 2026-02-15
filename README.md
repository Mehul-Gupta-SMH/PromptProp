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
  route.py           API endpoints (/api/inference, /api/jury, /api/refine)
  llm/
    llm_client.py    LiteLLM wrapper — unified generate() for all providers
    models.py        Pydantic models (ModelSettings, GenerateResponse, etc.)
  ppsecrets/         API key management (env vars)
  prompts/           Role definitions (manager, jury, rewriter)
  resources/         MLflow metrics integration
```

## Current Status

### Done
- **LLM Interaction Layer** — Generic `generate()` function via LiteLLM supporting Gemini, OpenAI, and Anthropic through a single interface
- **Backend API Endpoints** — `POST /api/inference`, `POST /api/jury`, `POST /api/refine` with Pydantic validation, CORS, and error handling
- **Frontend Migration** — React app moved to `ppFrontend/` with fetch-based API client replacing direct Gemini SDK calls
- **Multi-Provider Support** — Backend resolves model names to LiteLLM prefixes (`gemini/`, `openai/`, `anthropic/`)
- **Role Prompt Definitions** — Manager, Jury, and Rewriter prompts authored in `.prompt` files
- **MLflow Integration** — `registerMetrics.py` ready to log experiment metrics

### In Progress / Not Yet Wired
- Backend endpoints are functional but the role prompts (`.prompt` files) are not yet integrated into the API logic
- MLflow metric logging exists but nothing calls it yet
- `generateMetrics.py` is a stub
- `getPrompt.py` file paths don't match the actual prompt file locations
- No database layer (SQLAlchemy planned but not started)
- No tests

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Recharts, Tailwind CSS |
| Backend | FastAPI, Uvicorn, Python 3.10+ |
| LLM | LiteLLM (Gemini, OpenAI, Anthropic) |
| Tracking | MLflow (planned) |
| Database | SQLAlchemy (planned) |
| Testing | pytest (planned) |

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
