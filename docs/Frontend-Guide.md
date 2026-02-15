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

Uses native `fetch()` — no axios or other HTTP client dependency.

### `components/DatasetTable.tsx`
- Editable table for ground truth test cases
- CSV import support
- Fields: query, expectedOutput, softNegatives, hardNegatives

### `components/IterationChart.tsx`
- Recharts line graph: iteration number vs average score
- Only renders when 2+ iterations exist

### `types.ts`
TypeScript interfaces matching the backend Pydantic models:
- `LLMProvider` (gemini, openai, anthropic)
- `ModelSettings`, `JuryMember`, `DatasetRow`
- `TestCaseResult`, `IterationStep`, `AppState`

## Dev Proxy
`vite.config.ts` proxies `/api` requests to `http://localhost:8000` so the frontend and backend can run on different ports during development.
