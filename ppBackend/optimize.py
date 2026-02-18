"""
Backend optimization loop for PromptProp.

Runs the full inference -> jury -> refine cycle server-side and streams
progress to the frontend via Server-Sent Events (SSE).
"""

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Optional

from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from llm import generate, ModelSettings as LLMSettings, LLMError
from prompts.getPrompt import get_prompt
from db import (
    SessionLocal, Experiment, DatasetRow, JuryMember,
    PromptVersion, IterationResult, JuryEvaluation,
)
from resources.generateMetrics import compute_metrics
from resources.registerMetrics import register as mlflow_register

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REFINE_MODEL = "gemini/gemini-3-pro-preview"


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class RunnerModelPayload(BaseModel):
    provider: str = "gemini"
    model: str
    settings: Optional[dict] = None


class JuryMemberPayload(BaseModel):
    name: str
    provider: str = "gemini"
    model: str
    settings: Optional[dict] = None


class DatasetRowPayload(BaseModel):
    query: str
    expectedOutput: str
    softNegatives: Optional[str] = None
    hardNegatives: Optional[str] = None


class ManagerModelPayload(BaseModel):
    model: str = "gemini-3-pro-preview"
    settings: Optional[dict] = None


class OptimizeRequest(BaseModel):
    # --- Inline mode fields ---
    taskDescription: Optional[str] = None
    basePrompt: Optional[str] = None
    dataset: Optional[list[DatasetRowPayload]] = None
    juryMembers: Optional[list[JuryMemberPayload]] = None
    runnerModel: Optional[RunnerModelPayload] = None
    managerModel: Optional[ManagerModelPayload] = None

    # --- Experiment-ID mode ---
    experimentId: Optional[str] = None

    # --- Shared options ---
    maxIterations: int = Field(default=5, ge=1, le=20)
    convergenceThreshold: float = Field(default=0.2, ge=0.0)
    passThreshold: float = Field(default=90.0, ge=0.0, le=100.0)
    perfectScore: float = Field(default=98.0, ge=0.0, le=100.0)


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse(event: str, data: dict) -> str:
    """Format a single SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Model prefix resolver (duplicated from route.py to avoid circular import)
# ---------------------------------------------------------------------------

def _resolve_model(model: str) -> str:
    if "/" in model:
        return model
    if model.startswith("gemini"):
        return f"gemini/{model}"
    if model.startswith(("gpt", "o1", "o3")):
        return f"openai/{model}"
    if model.startswith("claude"):
        return f"anthropic/{model}"
    return model


# ---------------------------------------------------------------------------
# Helper: resolve inputs from request (inline or DB)
# ---------------------------------------------------------------------------

def _resolve_inputs(req: OptimizeRequest, db):
    """Return (experiment_id, task_desc, base_prompt, dataset_rows, jury_members, runner_model).

    In inline mode, creates an Experiment + DatasetRows + JuryMembers in DB.
    In experiment-ID mode, loads them from DB.
    """
    if req.experimentId:
        exp = db.query(Experiment).filter(Experiment.id == req.experimentId).first()
        if not exp:
            raise ValueError(f"Experiment {req.experimentId} not found.")

        rows = db.query(DatasetRow).filter(
            DatasetRow.experiment_id == exp.id,
            DatasetRow.split == "train",
        ).all()
        if not rows:
            rows = db.query(DatasetRow).filter(DatasetRow.experiment_id == exp.id).all()

        jury = db.query(JuryMember).filter(JuryMember.experiment_id == exp.id).all()

        dataset = [
            {"id": r.id, "query": r.query, "expectedOutput": r.expected_output,
             "softNegatives": r.soft_negatives, "hardNegatives": r.hard_negatives}
            for r in rows
        ]
        jury_list = [
            {"id": j.id, "name": j.name, "provider": j.provider,
             "model": j.model, "settings": j.settings}
            for j in jury
        ]
        runner = exp.runner_model
        return exp.id, exp.task_description, exp.base_prompt, dataset, jury_list, runner

    # Inline mode — create everything
    if not req.taskDescription or not req.basePrompt or not req.dataset or not req.juryMembers or not req.runnerModel:
        raise ValueError(
            "Inline mode requires taskDescription, basePrompt, dataset, juryMembers, and runnerModel."
        )

    exp = Experiment(
        task_description=req.taskDescription,
        base_prompt=req.basePrompt,
        runner_model={
            "provider": req.runnerModel.provider,
            "model": req.runnerModel.model,
            "settings": req.runnerModel.settings or {},
        },
    )
    db.add(exp)
    db.flush()

    dataset = []
    for row in req.dataset:
        db_row = DatasetRow(
            experiment_id=exp.id,
            split="train",
            query=row.query,
            expected_output=row.expectedOutput,
            soft_negatives=row.softNegatives,
            hard_negatives=row.hardNegatives,
        )
        db.add(db_row)
        db.flush()
        dataset.append({
            "id": db_row.id, "query": db_row.query,
            "expectedOutput": db_row.expected_output,
            "softNegatives": db_row.soft_negatives,
            "hardNegatives": db_row.hard_negatives,
        })

    jury_list = []
    for jm in req.juryMembers:
        db_jm = JuryMember(
            experiment_id=exp.id,
            name=jm.name,
            provider=jm.provider,
            model=jm.model,
            settings=jm.settings or {},
        )
        db.add(db_jm)
        db.flush()
        jury_list.append({
            "id": db_jm.id, "name": db_jm.name, "provider": db_jm.provider,
            "model": db_jm.model, "settings": db_jm.settings,
        })

    db.commit()

    runner = {
        "provider": req.runnerModel.provider,
        "model": req.runnerModel.model,
        "settings": req.runnerModel.settings or {},
    }
    return exp.id, req.taskDescription, req.basePrompt, dataset, jury_list, runner


# ---------------------------------------------------------------------------
# Helper: run inference for one row
# ---------------------------------------------------------------------------

async def _run_inference(runner: dict, task_desc: str, prompt: str, row: dict) -> tuple[str, dict]:
    """Run inference on a single dataset row. Returns (output_text, token_usage_dict)."""
    full_prompt = (
        f"Task Context: {task_desc}\n\n"
        f"Instruction: {prompt}\n\n"
        f"Input: {row['query']}"
    )
    messages = [{"role": "user", "content": full_prompt}]

    settings = None
    runner_settings = runner.get("settings") or {}
    if runner_settings:
        settings = LLMSettings(
            temperature=runner_settings.get("temperature", 0.7),
            top_p=runner_settings.get("topP"),
            top_k=runner_settings.get("topK"),
        )

    model_id = _resolve_model(runner.get("model", ""))
    result = await generate(model=model_id, messages=messages, settings=settings)
    usage = {"prompt_tokens": result.usage.prompt_tokens,
             "completion_tokens": result.usage.completion_tokens,
             "total_tokens": result.usage.total_tokens}
    return result.content or "No response generated.", usage


# ---------------------------------------------------------------------------
# Helper: run jury panel on one row
# ---------------------------------------------------------------------------

async def _run_single_jury(jury: dict, task_desc: str, row: dict, actual_output: str) -> dict:
    """Evaluate output with a single jury member. Returns {name, score, reasoning}."""
    system_prompt = get_prompt("jury")

    user_prompt = (
        f"TASK CONTEXT: {task_desc}\n"
        f"USER QUERY: {row['query']}\n"
        f"EXPECTED OUTPUT: {row['expectedOutput']}\n"
        f"SOFT NEGATIVES: {row.get('softNegatives') or 'None'}\n"
        f"HARD NEGATIVES: {row.get('hardNegatives') or 'None'}\n\n"
        f'AI OUTPUT TO EVALUATE:\n"""\n{actual_output}\n"""\n\n'
        'Return a JSON object with exactly two keys: '
        '"score" (number from 0 to 100) and "reasoning" (string with detailed critique). '
        "Be strict. If it hits a hard negative, score below 40."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    jury_settings = jury.get("settings") or {}
    settings = LLMSettings(
        temperature=jury_settings.get("temperature", 0),
        top_p=jury_settings.get("topP"),
        top_k=jury_settings.get("topK"),
    )

    model_id = _resolve_model(jury.get("model", ""))

    try:
        result = await generate(
            model=model_id,
            messages=messages,
            settings=settings,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(result.content)
        usage = {"prompt_tokens": result.usage.prompt_tokens,
                 "completion_tokens": result.usage.completion_tokens,
                 "total_tokens": result.usage.total_tokens}
        return {
            "juryName": jury["name"],
            "juryMemberId": jury["id"],
            "score": float(parsed.get("score", 0)),
            "reasoning": parsed.get("reasoning", "No reasoning provided."),
            "tokenUsage": usage,
        }
    except (json.JSONDecodeError, KeyError):
        return {
            "juryName": jury["name"],
            "juryMemberId": jury["id"],
            "score": 0,
            "reasoning": "Error parsing jury response.",
            "tokenUsage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }


async def _run_jury_panel(jury_members: list[dict], task_desc: str, row: dict, actual_output: str) -> list[dict]:
    """Run all jury members in parallel for one row."""
    return await asyncio.gather(
        *[_run_single_jury(j, task_desc, row, actual_output) for j in jury_members]
    )


# ---------------------------------------------------------------------------
# Helper: run refinement
# ---------------------------------------------------------------------------

async def _run_refinement(task_desc: str, prompt: str, failures: str,
                          model: str | None = None, settings_override: dict | None = None) -> dict:
    """Call the rewriter model to refine the prompt. Returns {explanation, refinedPrompt, deltaReasoning}."""
    system_prompt = get_prompt("rewriter")

    user_prompt = (
        f"TASK: {task_desc}\n\n"
        f'CURRENT PROMPT:\n"""\n{prompt}\n"""\n\n'
        f"CRITIQUE FROM FAILED TEST CASES (BACK-PROPAGATED ERROR):\n{failures}\n\n"
        "Return a JSON object with exactly three keys: "
        '"explanation" (string), "refinedPrompt" (string), "deltaReasoning" (string).'
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Use manager model settings if provided, otherwise default
    mgr_settings = settings_override or {}
    settings = LLMSettings(
        temperature=mgr_settings.get("temperature", 0.2),
        top_p=mgr_settings.get("topP"),
        top_k=mgr_settings.get("topK"),
    )
    resolved_model = _resolve_model(model) if model else REFINE_MODEL

    try:
        result = await generate(
            model=resolved_model,
            messages=messages,
            settings=settings,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(result.content)
        usage = {"prompt_tokens": result.usage.prompt_tokens,
                 "completion_tokens": result.usage.completion_tokens,
                 "total_tokens": result.usage.total_tokens}
        return {
            "explanation": parsed.get("explanation", "Failed to refine."),
            "refinedPrompt": parsed.get("refinedPrompt", prompt),
            "deltaReasoning": parsed.get("deltaReasoning", "None"),
            "tokenUsage": usage,
        }
    except (json.JSONDecodeError, KeyError):
        return {
            "explanation": "Failed to refine.",
            "refinedPrompt": prompt,
            "deltaReasoning": "None",
            "tokenUsage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }


# ---------------------------------------------------------------------------
# Main optimization stream generator
# ---------------------------------------------------------------------------

async def _optimize_stream(req: OptimizeRequest) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE events for the optimization loop."""
    db = SessionLocal()
    try:
        # Resolve inputs
        try:
            experiment_id, task_desc, base_prompt, dataset, jury_members, runner = \
                _resolve_inputs(req, db)
        except ValueError as e:
            yield _sse("error", {"stage": "setup", "message": str(e)})
            return

        current_prompt = base_prompt
        prev_score = -1.0

        # Cumulative token tracking
        total_usage = {"inference": 0, "jury": 0, "refinement": 0, "total": 0}

        yield _sse("start", {
            "experimentId": experiment_id,
            "totalRows": len(dataset),
            "totalJury": len(jury_members),
            "maxIterations": req.maxIterations,
        })

        for iteration in range(1, req.maxIterations + 1):
            # Create PromptVersion in DB
            pv = PromptVersion(
                experiment_id=experiment_id,
                iteration_number=iteration,
                prompt_text=current_prompt,
            )
            db.add(pv)
            db.flush()

            yield _sse("iteration_start", {
                "iteration": iteration,
                "promptText": current_prompt,
                "promptVersionId": pv.id,
            })

            # Process each dataset row
            all_results = []
            iter_usage = {"inference": 0, "jury": 0, "refinement": 0}
            for row_idx, row in enumerate(dataset):
                # 1. Inference
                try:
                    actual_output, inf_usage = await _run_inference(runner, task_desc, current_prompt, row)
                except LLMError as e:
                    yield _sse("error", {"stage": "inference", "message": str(e), "iteration": iteration, "rowIndex": row_idx})
                    return

                iter_usage["inference"] += inf_usage["total_tokens"]
                total_usage["inference"] += inf_usage["total_tokens"]
                total_usage["total"] += inf_usage["total_tokens"]

                yield _sse("inference_result", {
                    "iteration": iteration,
                    "rowIndex": row_idx,
                    "rowId": row["id"],
                    "actualOutput": actual_output,
                    "tokenUsage": inf_usage,
                })

                # 2. Jury evaluation (parallel across jury members)
                try:
                    jury_evals = await _run_jury_panel(jury_members, task_desc, row, actual_output)
                except LLMError as e:
                    yield _sse("error", {"stage": "jury", "message": str(e), "iteration": iteration, "rowIndex": row_idx})
                    return

                jury_tokens = sum(e.get("tokenUsage", {}).get("total_tokens", 0) for e in jury_evals)
                iter_usage["jury"] += jury_tokens
                total_usage["jury"] += jury_tokens
                total_usage["total"] += jury_tokens

                avg_score = sum(e["score"] for e in jury_evals) / len(jury_evals) if jury_evals else 0
                combined_feedback = "\n".join(
                    f"[{e['juryName']}]: {e['reasoning']}" for e in jury_evals
                )

                # 3. Store IterationResult + JuryEvaluations in DB
                ir = IterationResult(
                    prompt_version_id=pv.id,
                    dataset_row_id=row["id"],
                    actual_output=actual_output,
                    average_score=avg_score,
                    combined_feedback=combined_feedback,
                )
                db.add(ir)
                db.flush()

                for ev in jury_evals:
                    je = JuryEvaluation(
                        iteration_result_id=ir.id,
                        jury_member_id=ev["juryMemberId"],
                        jury_name=ev["juryName"],
                        score=ev["score"],
                        reasoning=ev["reasoning"],
                    )
                    db.add(je)

                db.flush()

                all_results.append({
                    "rowId": row["id"],
                    "actualOutput": actual_output,
                    "scores": [{"juryName": e["juryName"], "score": e["score"], "reasoning": e["reasoning"]} for e in jury_evals],
                    "averageScore": avg_score,
                    "combinedFeedback": combined_feedback,
                })

                yield _sse("jury_result", {
                    "iteration": iteration,
                    "rowIndex": row_idx,
                    "rowId": row["id"],
                    "scores": [{"juryName": e["juryName"], "score": e["score"], "reasoning": e["reasoning"]} for e in jury_evals],
                    "averageScore": avg_score,
                })

            # Compute iteration metrics
            iteration_avg = sum(r["averageScore"] for r in all_results) / len(all_results) if all_results else 0
            metrics_input = [{"score": r["averageScore"], "reasoning": r["combinedFeedback"]} for r in all_results]
            metrics = compute_metrics(metrics_input, pass_threshold=req.passThreshold)

            # Log to MLflow
            mlflow_run_id = mlflow_register(
                experiment_name=experiment_id,
                metrics_dict=metrics,
                iteration=iteration,
                prompt_text=current_prompt,
                token_usage=iter_usage,
                run_name=f"iteration-{iteration}",
            )

            # Update PromptVersion average score
            pv.average_score = iteration_avg
            db.commit()

            converged = (
                iteration_avg >= req.perfectScore
                or (prev_score >= 0 and abs(iteration_avg - prev_score) < req.convergenceThreshold)
            )

            yield _sse("iteration_complete", {
                "iteration": iteration,
                "averageScore": round(iteration_avg, 2),
                "metrics": metrics,
                "mlflowRunId": mlflow_run_id,
                "converged": converged,
                "results": all_results,
                "iterationTokens": iter_usage,
                "cumulativeTokens": dict(total_usage),
            })

            if converged:
                break

            # Refinement: collect failures and refine prompt
            failures_text = "\n---\n".join(
                f"Query: {row['query']}\nExpected: {row['expectedOutput']}\n"
                f"Actual: {r['actualOutput']}\nCritique: {r['combinedFeedback']}"
                for r, row in zip(all_results, dataset)
                if r["averageScore"] < req.passThreshold
            )

            if failures_text:
                try:
                    mgr_model = req.managerModel.model if req.managerModel else None
                    mgr_settings = req.managerModel.settings if req.managerModel else None
                    refinement = await _run_refinement(
                        task_desc, current_prompt, failures_text,
                        model=mgr_model, settings_override=mgr_settings,
                    )
                except LLMError as e:
                    yield _sse("error", {"stage": "refinement", "message": str(e), "iteration": iteration})
                    return

                ref_tokens = refinement.get("tokenUsage", {}).get("total_tokens", 0)
                total_usage["refinement"] += ref_tokens
                total_usage["total"] += ref_tokens

                pv.refinement_feedback = refinement["explanation"]
                pv.refinement_meta = {
                    "deltaReasoning": refinement["deltaReasoning"],
                }
                db.commit()

                yield _sse("refinement", {
                    "iteration": iteration,
                    "explanation": refinement["explanation"],
                    "refinedPrompt": refinement["refinedPrompt"],
                    "deltaReasoning": refinement["deltaReasoning"],
                    "tokenUsage": refinement.get("tokenUsage"),
                    "cumulativeTokens": dict(total_usage),
                })

                current_prompt = refinement["refinedPrompt"]
            else:
                yield _sse("refinement", {
                    "iteration": iteration,
                    "explanation": "All test cases passed. No refinement needed.",
                    "refinedPrompt": current_prompt,
                    "deltaReasoning": "No failures to analyze.",
                })

            prev_score = iteration_avg

        # Mark experiment complete
        exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if exp:
            exp.is_complete = True
            db.commit()

        yield _sse("complete", {
            "experimentId": experiment_id,
            "finalScore": round(iteration_avg, 2),
            "finalPrompt": current_prompt,
            "totalIterations": iteration,
            "totalTokens": dict(total_usage),
        })

    except Exception as e:
        logger.exception("Optimization stream error")
        yield _sse("error", {"stage": "unknown", "message": str(e)})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Public: create the StreamingResponse
# ---------------------------------------------------------------------------

def optimize_endpoint(req: OptimizeRequest) -> StreamingResponse:
    """Create a StreamingResponse that streams SSE events for the optimization loop."""
    return StreamingResponse(
        _optimize_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
