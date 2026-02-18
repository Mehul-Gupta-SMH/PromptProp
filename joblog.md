# Job Log

Tracks pending and completed tasks for commit management.

## Session: 2026-02-18

### Pending Changes Identified

All changes below are from previous session work that was not committed.

| # | Commit Group | Files | Status |
|---|-------------|-------|--------|
| 1 | chore: Add .env to .gitignore and load dotenv at startup | `.gitignore`, `ppBackend/main.py`, `requirements.txt` | done |
| 2+3 | feat: Backend optimization loop + model discovery | `ppBackend/models_list.py`, `ppBackend/optimize.py`, `ppBackend/route.py` | done |
| 4 | feat: Revamp frontend to use SSE optimization and multi-provider models | `ppFrontend/App.tsx`, `ppFrontend/services/apiService.ts`, `ppFrontend/types.ts`, `ppFrontend/index.html` | done |
| 5 | docs: Update TASKS.md with completed task checkmarks | `TASKS.md` | done |
| 6 | chore: Track package-lock.json | `ppFrontend/package-lock.json` | done |

### Excluded from commits
- `ppBackend/mlruns/` — MLflow runtime data, should be gitignored
- `.claude/` — Claude Code local settings, should be gitignored

### Commit Log

| Hash | Message |
|------|---------|
| `c0c87e8` | chore: Add .env to gitignore, load dotenv at startup, add httpx dep |
| `21d85b1` | feat: Add backend optimization loop with SSE streaming and model discovery |
| `eba357e` | feat: Revamp frontend to use SSE optimization and multi-provider models |
| `8912397` | docs: Mark completed tasks in TASKS.md |
| `7125b32` | chore: Track frontend package-lock.json for reproducible installs |

### Notes
- Merged commits 2 & 3 into one since `route.py` imports both `models_list` and `optimize`
- Added `mlruns/` and `.claude/` to `.gitignore` to exclude runtime/local data
- Branch is 5 commits ahead of `origin/main` — not pushed yet

---

## Session: 2026-02-18 (Test Suite + README)

### Changes

| # | Commit Group | Files | Status |
|---|-------------|-------|--------|
| 1 | test: Add backend test infrastructure | `ppBackend/pytest.ini`, `ppBackend/requirements-test.txt`, `ppBackend/tests/__init__.py`, `ppBackend/tests/conftest.py`, `ppBackend/tests/unit/__init__.py`, `ppBackend/tests/integration/__init__.py`, `ppBackend/tests/regression/__init__.py` | pending |
| 2 | test: Add unit tests for backend modules | `ppBackend/tests/unit/test_resolve_model.py`, `test_generate_metrics.py`, `test_sse_helper.py`, `test_sort_models.py`, `test_secrets.py`, `test_llm_models.py`, `test_llm_client.py`, `test_get_prompt.py` | pending |
| 3 | test: Add integration tests for API endpoints and DB | `ppBackend/tests/integration/test_api_health.py`, `test_api_inference.py`, `test_api_jury.py`, `test_api_refine.py`, `test_api_metrics.py`, `test_api_dataset.py`, `test_api_models.py`, `test_api_optimize.py`, `test_db_models.py` | pending |
| 4 | test: Add regression tests | `ppBackend/tests/regression/test_json_fallbacks.py`, `test_autosplit_math.py`, `test_convergence_logic.py`, `test_metrics_contract.py` | pending |
| 5 | docs: Update README to reflect current project state | `README.md` | pending |

### Test Results
- 146 tests passing (82 unit, 44 integration, 20 regression)
- 91% overall coverage
- Key files: route.py 98%, optimize.py 88%, llm_client.py 100%, generateMetrics.py 100%, db/models.py 100%

---

## Session: 2026-02-18 (Experiments + Deep Health-Check)

### Changes

| # | Commit Group | Files | Status |
|---|-------------|-------|--------|
| 1 | feat: Add experiment runner script and deep health-check endpoint | `ppBackend/run_experiments.py` (new), `ppBackend/route.py` | done |

### Commit Log

| Hash | Message |
|------|---------|
| `1437443` | feat: Add experiment runner script and deep health-check endpoint |

### Experiment Results

Ran 3 text classification experiments through `/api/optimize` SSE endpoint using `gpt-4o-mini`:

| Experiment | Rows | Iterations | Final Score | Experiment ID |
|---|---|---|---|---|
| Easy — Binary Sentiment | 3 | 1 | 100.0 | `ab98cebb-0344-4e22-9c21-67bc90dcb445` |
| Medium — 4-Category Feedback | 5 | 1 | 100.0 | `e8e8ddf1-11a7-4c59-b615-7ed153d5754b` |
| Hard — 6-Category Intent Detection | 6 | 2 | 98.3 | `77e4687e-5e1c-4a50-8a43-571785761f5c` |

- All experiments persisted to SQLite and MLflow
- DB verification via `GET /api/dataset/{id}` confirmed correct row counts

### Deep Health-Check

Enhanced `GET /health-check?deep=true` validates API keys against provider endpoints:
- **OpenAI**: `/v1/models` + optional billing fetch
- **Gemini**: `/v1/models` with API key
- **Anthropic**: `/v1/messages/count_tokens` (cheapest call, no model invocation)

Status levels: `ok` / `warning` (valid key, no credits) / `error` / `missing`
Overall: `healthy` / `healthy (with warnings)` / `degraded`

### Notes
- Easy and Medium experiments scored 100% on first iteration — base prompts were sufficient
- Hard experiment needed 2 iterations; some rows scored 90 in iteration 1, converged at 98.3 (above 98% perfectScore threshold)
- Anthropic key detected as valid but out of credits (warning, not error)
