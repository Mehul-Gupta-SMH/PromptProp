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
