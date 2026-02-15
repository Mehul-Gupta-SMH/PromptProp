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

| Parameter | Value | Location |
|-----------|-------|----------|
| Max iterations | 5 | `App.tsx` |
| Convergence threshold | 98% avg score | `App.tsx` |
| Plateau detection | Score delta < 0.2 | `App.tsx` |
| Failure threshold | Score < 90 | `App.tsx` |
| Refinement model | `gemini-3-pro-preview` | `route.py` |
| Refinement temperature | 0.2 | `route.py` |

## Scoring System

- Each jury member independently scores 0-100
- Hard negative violations trigger scores below 40
- Scores are averaged across all jury members per test case
- Iteration score = average of all test case scores
