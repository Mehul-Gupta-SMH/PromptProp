# PromptProp — Agent Skill Definition

## Skill Metadata

| Field | Value |
|-------|-------|
| **Name** | `promptprop` |
| **Display Name** | PromptProp: Prompt Back-Propagation Optimizer |
| **Version** | 1.0.0 |
| **Category** | Prompt Engineering / LLM Tooling |
| **Transport** | HTTP REST + SSE |
| **Base URL** | `http://localhost:8000` |
| **Auth** | None (local tool — API keys configured server-side via env vars) |

---

## Description

PromptProp is an iterative prompt optimizer that applies back-propagation concepts to natural language instructions. Given a task description, a seed prompt, a ground-truth dataset, and an AI jury panel, it runs an automated loop — inference, jury scoring, failure analysis, prompt rewriting — until the prompt converges on high quality.

**When to use this skill:**
- You need to improve an LLM prompt systematically against a test dataset
- You want to evaluate prompt quality with multi-model jury scoring
- You need to refine a prompt based on structured failure analysis
- You want to browse or replay past optimization experiments

---

## Capabilities

### 1. Prompt Optimization (Primary)
Run a full optimization loop that iteratively refines a prompt. The loop:
1. Runs inference on every dataset row using the current prompt
2. Scores each output with a jury of AI models (0-100)
3. Checks convergence (avg >= 98% or delta < 0.2)
4. Collects failures (score < 90) and rewrites the prompt
5. Repeats up to N iterations

### 2. Individual LLM Operations
- **Inference**: Run a prompt + query through any supported LLM
- **Jury Evaluation**: Score an output against expected answer
- **Prompt Refinement**: Rewrite a prompt given failure feedback

### 3. Dataset Management
- Upload dataset rows with train/val/test splits
- Auto-split datasets by configurable ratios
- Query dataset statistics and rows by split

### 4. Experiment History
- List past experiments with summary statistics
- Retrieve full experiment detail (iterations, scores, prompts, jury evaluations)
- Replay or load past experiments

### 5. Model Discovery
- List available LLM models across configured providers (Gemini, OpenAI, Anthropic)

---

## API Reference

### Core Endpoints

#### `POST /api/optimize` — Run Optimization Loop (SSE Stream)

Starts a full optimization loop and streams progress via Server-Sent Events.

**Request Body:**
```json
{
  "taskDescription": "Categorize customer feedback into Product, Billing, Shipping, or General",
  "basePrompt": "You are a professional assistant. Help the user with their request.",
  "dataset": [
    {
      "query": "My package hasn't arrived yet",
      "expectedOutput": "Shipping",
      "softNegatives": "General",
      "hardNegatives": "Billing"
    }
  ],
  "juryMembers": [
    {
      "name": "Senior Analyst",
      "provider": "gemini",
      "model": "gemini-3-pro-preview",
      "settings": { "temperature": 0 }
    }
  ],
  "runnerModel": {
    "provider": "gemini",
    "model": "gemini-3-flash-preview",
    "settings": { "temperature": 0.1 }
  },
  "managerModel": {
    "model": "gemini-3-pro-preview",
    "settings": { "temperature": 0.2 }
  },
  "maxIterations": 5,
  "convergenceThreshold": 0.2,
  "passThreshold": 90.0,
  "perfectScore": 98.0
}
```

**SSE Events:**
| Event | Description | Key Data Fields |
|-------|-------------|-----------------|
| `start` | Optimization begun | `experimentId` |
| `iteration_start` | New cycle starting | `iteration`, `promptText` |
| `inference_result` | Single inference done | `iteration`, `rowIndex` |
| `jury_result` | Row fully scored | `rowId`, `scores`, `averageScore` |
| `iteration_complete` | Cycle finished | `iteration`, `averageScore`, `converged`, `results` |
| `refinement` | Prompt rewritten | `refinedPrompt`, `explanation`, `deltaReasoning` |
| `complete` | Optimization done | `finalScore`, `totalTokens`, `experimentId` |
| `error` | Error occurred | `stage`, `message` |

---

#### `POST /api/inference` — Single Inference

```json
// Request
{
  "model": "gemini-3-flash-preview",
  "taskDescription": "Categorize feedback",
  "promptTemplate": "Classify this into a category",
  "query": "My package is late",
  "settings": { "temperature": 0.1 }
}

// Response
{ "output": "Shipping" }
```

---

#### `POST /api/jury` — Evaluate Output

```json
// Request
{
  "juryModel": "gemini-3-pro-preview",
  "jurySettings": { "temperature": 0 },
  "taskDescription": "Categorize feedback",
  "row": {
    "query": "My package is late",
    "expectedOutput": "Shipping",
    "softNegatives": "General",
    "hardNegatives": "Billing"
  },
  "actualOutput": "Shipping"
}

// Response
{ "score": 95.0, "reasoning": "Correctly identified as Shipping category..." }
```

---

#### `POST /api/refine` — Refine Prompt from Failures

```json
// Request
{
  "taskDescription": "Categorize feedback",
  "currentPrompt": "You are a classifier...",
  "failures": "[judge-1]: Score 40 — Misclassified billing issue..."
}

// Response
{
  "explanation": "The prompt lacked explicit billing keywords...",
  "refinedPrompt": "You are a precise classifier. Always check for...",
  "deltaReasoning": "Added explicit billing trigger words..."
}
```

---

### Dataset Endpoints

#### `POST /api/dataset` — Upload Dataset
```json
// Request
{
  "experimentId": "uuid",
  "rows": [
    { "query": "q1", "expectedOutput": "e1", "split": "train" }
  ],
  "autoSplit": true,
  "trainRatio": 0.70,
  "valRatio": 0.15,
  "testRatio": 0.15
}

// Response
{ "experimentId": "uuid", "splits": { "train": 7, "val": 2, "test": 1, "total": 10 }, "rowIds": ["..."] }
```

#### `GET /api/dataset/{experiment_id}` — Dataset Split Stats
#### `GET /api/dataset/{experiment_id}/{split}` — Get Rows by Split

---

### Experiment History Endpoints

#### `GET /api/experiments?limit=50&offset=0` — List Experiments

```json
// Response
{
  "experiments": [
    {
      "id": "uuid",
      "name": null,
      "taskDescription": "Categorize feedback",
      "basePrompt": "You are a classifier...",
      "runnerModel": { "provider": "gemini", "model": "gemini-3-flash-preview" },
      "isComplete": true,
      "createdAt": "2026-02-19T10:00:00Z",
      "updatedAt": "2026-02-19T10:05:00Z",
      "iterationCount": 3,
      "bestScore": 95.5,
      "finalScore": 95.5,
      "datasetSize": 10
    }
  ],
  "total": 1
}
```

#### `GET /api/experiments/{id}` — Full Experiment Detail

Returns nested structure: experiment metadata, jury members, dataset rows, and prompt versions (each containing per-row iteration results with jury evaluations).

---

### Utility Endpoints

#### `GET /api/models?refresh=false` — Available LLM Models
Returns models grouped by provider. Set `refresh=true` to bypass cache.

#### `GET /health-check?deep=false` — Health Check
Set `deep=true` to validate each configured API key against its provider.

#### `POST /api/metrics` — Log Iteration Metrics to MLflow

---

## Supported Models

Model names follow LiteLLM conventions. Bare names are auto-prefixed:

| Input | Resolved |
|-------|----------|
| `gemini-3-pro-preview` | `gemini/gemini-3-pro-preview` |
| `gpt-4o` | `openai/gpt-4o` |
| `claude-sonnet-4-5-20250929` | `anthropic/claude-sonnet-4-5-20250929` |
| `openai/gpt-4o` | `openai/gpt-4o` (passthrough) |

---

## Agent Integration Patterns

### Pattern 1: Full Optimization (Recommended)

```
1. POST /api/optimize with task, prompt, dataset, jury config
2. Consume SSE stream until "complete" event
3. Extract finalScore and experimentId from complete event
4. GET /api/experiments/{experimentId} to retrieve the optimized prompt
```

### Pattern 2: Manual Step-by-Step

```
1. POST /api/inference for each dataset row
2. POST /api/jury for each (row, output) pair
3. Collect failures (score < threshold)
4. POST /api/refine with failure summaries
5. Repeat with refined prompt
```

### Pattern 3: Evaluate Only

```
1. POST /api/jury for each test case to score an existing prompt
2. POST /api/metrics to log results
```

### Pattern 4: Historical Analysis

```
1. GET /api/experiments to list past runs
2. GET /api/experiments/{id} for full detail
3. Compare prompt versions and scores across iterations
```

---

## Prerequisites

- Python 3.10+, Node.js 18+
- At least one API key env var: `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`
- Backend: `cd ppBackend && pip install -r ../requirements.txt && python main.py` (port 8000)
- Frontend (optional): `cd ppFrontend && npm install && npm run dev` (port 3000)

---

## Error Handling

| HTTP Code | Meaning |
|-----------|---------|
| 200 | Success |
| 404 | Experiment/resource not found |
| 422 | Validation error (missing/invalid fields) |
| 502 | LLM provider error (auth, rate limit, bad request) |
| 501 | Endpoint not yet implemented |

All error responses include a `detail` field with a human-readable message.
