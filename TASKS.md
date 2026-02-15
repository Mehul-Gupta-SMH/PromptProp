# PromptProp — Task Board

## Core Backend

### [ ] Integrate role prompts into API endpoints
**Labels:** `backend` `enhancement`

The `ppBackend/prompts/` directory contains well-authored role definitions (`manager.prompt`, `jury.prompt`, `rewriter.prompt`) but they are not used by the API endpoints. The current `/api/jury` and `/api/refine` endpoints have prompt logic hardcoded inline.

**Requirements:**
- Load `.prompt` files at startup or on-demand via a prompt loader
- Fix `getPrompt.py` — current file paths (`systemPrompts/`, `userPrompts/`) don't match actual file locations
- Use `jury.prompt` content as the system message for `/api/jury`
- Use `rewriter.prompt` content as the system message for `/api/refine`
- Use `manager.prompt` to orchestrate the overall flow when the backend takes over the loop

**Files:** `ppBackend/prompts/getPrompt.py`, `ppBackend/prompts/*.prompt`, `ppBackend/route.py`

---

### [ ] Add SQLAlchemy database layer for experiment persistence
**Labels:** `backend` `enhancement`

Currently all state lives in the frontend React state and is lost on page refresh. The backend needs a persistence layer.

**Requirements:**
- Add SQLAlchemy to `requirements.txt`
- Design schema for: Experiments, Datasets (train/val/test splits), IterationResults, PromptVersions, JuryEvaluations
- Create models in `ppBackend/models/` or `ppBackend/db/`
- Add database session management (connection pooling, migrations)
- Support SQLite for dev, PostgreSQL for prod (configurable via `configs/*.yaml`)

**References:** `ppBackend/Instructions.md` lists SQLAlchemy as planned tech. `manager.prompt` describes train/val/test split management.

---

### [ ] Wire MLflow experiment tracking into optimization loop
**Labels:** `backend` `enhancement`

`ppBackend/resources/registerMetrics.py` has a working `register()` function that logs metrics to MLflow, but nothing calls it.

**Requirements:**
- Call `registerMetrics.register()` after each jury evaluation round
- Log per-iteration metrics: average score, per-case scores, token usage
- Log prompt versions as MLflow artifacts
- Track traditional metrics (accuracy, precision, recall) once `generateMetrics.py` is implemented
- Add MLflow to `requirements.txt`
- Add MLflow server configuration to `configs/*.yaml`

**Files:** `ppBackend/resources/registerMetrics.py` (existing), `ppBackend/resources/generateMetrics.py` (stub)

---

### [ ] Implement generateMetrics.py — traditional + custom metrics
**Labels:** `backend` `enhancement`

`ppBackend/resources/generateMetrics.py` has a single stub function `traditionalMetrics()`. The manager prompt specifies both traditional and non-traditional metrics.

**Requirements:**
- **Traditional metrics**: Accuracy, Precision, Recall computed from jury scores vs thresholds
- **Non-traditional metrics** (from `manager.prompt`):
  - Directness: How efficiently the prompt reaches the objective
  - Format Adherence: Compliance with specified output formats
  - Consistency: Reliability across different input variations
  - Relevance: Alignment with user intent
- Return metrics as a dict compatible with `registerMetrics.register()`

**Files:** `ppBackend/resources/generateMetrics.py`, `ppBackend/prompts/manager.prompt`

---

### [ ] Implement train/validation/test data split endpoints
**Labels:** `backend` `enhancement`

The backend has stub endpoints for `POST /train_data`, `POST /validation_data`, `POST /test_data` that return 501.

**Requirements:**
- Accept dataset upload (JSON array of {query, expectedOutput, softNegatives, hardNegatives})
- Implement automatic splitting (e.g., 70/15/15) or accept pre-split data
- Store splits in the database
- Return split statistics
- Use validation set for iterative improvement, test set for final evaluation only

**Depends on:** SQLAlchemy database layer

---

### [ ] Move optimization loop to backend
**Labels:** `backend` `enhancement`

The optimization loop currently runs in the frontend `App.tsx`. For robustness, multi-provider support, and proper data management, it should move to the backend.

**Requirements:**
- New endpoint: `POST /api/optimize` — accepts task description, base prompt, dataset, jury config, max iterations
- Backend orchestrates the full loop using the manager role prompt
- Stream progress updates to frontend (SSE or WebSocket)
- Store each iteration's results in the database
- Frontend becomes a thin UI that starts optimization and displays progress
- Keep existing per-step endpoints as building blocks

**Depends on:** SQLAlchemy database layer, role prompt integration, metrics pipeline

---

## Frontend Enhancements

### [ ] Add local persistence with IndexedDB
**Labels:** `frontend` `enhancement`

Frontend state is lost on page refresh.

**Requirements:**
- Use IndexedDB (via idb or Dexie.js) to persist: dataset rows, optimization history, task description, base prompt, jury panel config
- Auto-save on changes, auto-load on startup
- Add "Clear Saved Data" option

---

### [ ] Add comparative prompt diff view between iterations
**Labels:** `frontend` `enhancement`

The current diff in `App.tsx` uses a simple line-based comparison (`getLineDiff`). It misses inline changes and doesn't handle reordering well.

**Requirements:**
- Use a proper diff library (e.g., `diff` npm package)
- Show side-by-side or unified diff between any two iterations
- Highlight inline word-level changes
- Add iteration selector dropdown to compare arbitrary iterations

---

### [ ] Add Few-Shot example injection engine
**Labels:** `frontend` `backend` `enhancement`

After optimization, successful test cases could be automatically extracted and injected as few-shot examples in the refined prompt.

**Requirements:**
- After each iteration, identify top-scoring test cases (score >= 95)
- Format them as few-shot examples (input → output pairs)
- Inject into the prompt template before the next iteration
- Allow user to toggle this on/off
- Cap at N examples to avoid prompt length explosion

---

### [ ] Add token usage monitor
**Labels:** `frontend` `backend` `enhancement`

The backend `GenerateResponse` already returns `TokenUsage` (prompt_tokens, completion_tokens, total_tokens) but the frontend doesn't display it.

**Requirements:**
- Track cumulative token usage across all API calls in an optimization run
- Display real-time token counter in the progress panel
- Show per-iteration breakdown (inference tokens vs jury tokens vs refinement tokens)
- Optionally show estimated cost based on provider pricing

---

### [ ] Add Golden Prompt export (JSON, Python, Markdown)
**Labels:** `frontend` `enhancement`

**Requirements:**
- After optimization completes, add an "Export" button for the best-performing prompt
- Export formats:
  - **JSON**: `{ "prompt": "...", "model": "...", "settings": {...}, "score": 95.2 }`
  - **Python**: Ready-to-use snippet with LiteLLM or OpenAI SDK
  - **Markdown**: Formatted prompt with metadata header
- Include optimization metadata (iterations, final score, jury config)

---

### [ ] Add synthetic edge-case data generation
**Labels:** `frontend` `backend` `enhancement`

**Requirements:**
- Button to auto-generate test cases based on the task description
- Use LLM to create edge cases that are likely to trip up the prompt
- Include both positive examples and adversarial/tricky cases
- Generate soft/hard negatives automatically
- Add generated cases to the dataset table for user review before optimization

---

### [ ] Add Human-in-the-Loop: pause and override jury scores
**Labels:** `frontend` `enhancement`

**Requirements:**
- Add a "Pause & Override" mode during optimization
- After jury scoring, show results to user before refinement
- Allow user to manually adjust scores or add feedback
- User can approve, modify, or skip the refinement step
- Resume optimization with user-corrected data

---

### [ ] Add multi-provider model selector in UI
**Labels:** `frontend` `enhancement`

The `LLMProvider` enum now includes Gemini, OpenAI, and Anthropic but the UI only shows Gemini models in the dropdown.

**Requirements:**
- Group models by provider in the model selector
- Add common models: GPT-4o, GPT-4o-mini, Claude Sonnet, Claude Haiku
- Allow custom model name entry for newer models
- Update jury member creation to support selecting different providers

---

## Testing & DevOps

### [ ] Add pytest test suite for backend
**Labels:** `backend` `testing`

**Requirements:**
- Set up pytest with conftest.py for fixtures
- Unit tests for:
  - `llm/llm_client.py` — mock LiteLLM calls, test error handling, test configure_api_keys
  - `llm/models.py` — test Pydantic validation
  - `route.py` — test each endpoint with FastAPI TestClient
  - `ppsecrets/getSecrets.py` — test with mocked env vars
  - `configs/getConfig.py` — test YAML loading
- Integration tests for the full inference → jury → refine flow (with mocked LLM)
- Target 80% coverage per Instructions.md

---

### [ ] Add HTTP test files for API endpoints
**Labels:** `backend` `testing`

**Requirements:**
- Create `.http` files (compatible with VS Code REST Client / IntelliJ) for:
  - `GET /health-check`
  - `POST /api/inference`
  - `POST /api/jury`
  - `POST /api/refine`
- Include example request bodies with realistic test data
- Place in `ppBackend/tests/` or `ppBackend/http/`

---

## Advanced Features

### [ ] Variable injection with dynamic placeholders
**Labels:** `enhancement`

**Requirements:**
- Support `{{variable_name}}` placeholders in prompts
- Define a schema for variables (name, type, description, default)
- Validate variables before optimization starts
- Inject actual values during inference
- UI for managing variable definitions

---

### [ ] Benchmarking mode: parallel seed prompt testing
**Labels:** `enhancement`

**Requirements:**
- Allow users to provide multiple starting prompts
- Run optimization in parallel for each seed
- Compare convergence speed and final scores
- Recommend the best-performing seed
- Display comparison chart

---

### [ ] Prompt linting: static analysis for common pitfalls
**Labels:** `enhancement`

**Requirements:**
- Analyze prompts before optimization for common issues:
  - Conflicting instructions
  - Ambiguous language
  - Missing output format specification
  - Overly long prompts
  - Redundant instructions
- Show warnings/suggestions in the UI
- Optionally auto-fix simple issues
