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

## How Roles Interact

```
                    ┌──────────┐
                    │ Manager  │
                    │ (future) │
                    └────┬─────┘
                         │ orchestrates
              ┌──────────┼──────────┐
              ▼                     ▼
        ┌──────────┐         ┌──────────┐
        │  Jury    │────────▶│ Rewriter │
        │ (scores) │ feedback│ (refines)│
        └──────────┘         └──────────┘
```
