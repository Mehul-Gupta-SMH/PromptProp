import json
import logging
import random

import fastapi
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Literal

from sqlalchemy.orm import Session
from fastapi import Depends

from llm import generate, ModelSettings as LLMSettings, LLMError
from prompts.getPrompt import get_prompt
from db import get_db, Experiment, DatasetRow
from resources.generateMetrics import compute_metrics
from resources.registerMetrics import register as mlflow_register, configure as mlflow_configure
from optimize import OptimizeRequest, optimize_endpoint
from models_list import get_available_models

logger = logging.getLogger(__name__)

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Model prefix resolver
# ---------------------------------------------------------------------------

def _resolve_model(model: str) -> str:
    """Prefix a bare model name with its LiteLLM provider prefix."""
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
# Request / Response schemas
# ---------------------------------------------------------------------------

class InferenceRequest(BaseModel):
    model: str
    taskDescription: str
    promptTemplate: str
    query: str
    settings: Optional[dict] = None

class InferenceResponse(BaseModel):
    output: str

class DatasetRowPayload(BaseModel):
    query: str
    expectedOutput: str
    softNegatives: Optional[str] = None
    hardNegatives: Optional[str] = None

class JuryRequest(BaseModel):
    juryModel: str
    jurySettings: Optional[dict] = None
    taskDescription: str
    row: DatasetRowPayload
    actualOutput: str

class JuryResponse(BaseModel):
    score: float
    reasoning: str

class RefineRequest(BaseModel):
    taskDescription: str
    currentPrompt: str
    failures: str

class RefineResponse(BaseModel):
    explanation: str
    refinedPrompt: str
    deltaReasoning: str


# --- Metrics endpoint ---

class TestCaseResultPayload(BaseModel):
    score: float
    reasoning: str = ""

class MetricsRequest(BaseModel):
    experimentId: str
    iteration: int
    results: list[TestCaseResultPayload]
    promptText: Optional[str] = None
    tokenUsage: Optional[dict] = None

class MetricsResponse(BaseModel):
    metrics: dict[str, float]
    mlflowRunId: Optional[str] = None


# --- Dataset endpoints ---

class DatasetRowInput(BaseModel):
    query: str
    expectedOutput: str
    softNegatives: Optional[str] = None
    hardNegatives: Optional[str] = None
    split: Optional[Literal["train", "val", "test"]] = None

class DatasetUploadRequest(BaseModel):
    experimentId: str
    rows: list[DatasetRowInput]
    autoSplit: bool = Field(default=False, description="Auto-split rows into train/val/test (70/15/15)")
    trainRatio: float = Field(default=0.70, ge=0.0, le=1.0)
    valRatio: float = Field(default=0.15, ge=0.0, le=1.0)
    testRatio: float = Field(default=0.15, ge=0.0, le=1.0)

class SplitStats(BaseModel):
    train: int
    val: int
    test: int
    total: int

class DatasetUploadResponse(BaseModel):
    experimentId: str
    splits: SplitStats
    rowIds: list[str]


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return JSONResponse({"message": "Welcome to the PromptProp Backend API!"})


@app.get("/health-check")
async def health_check():
    return JSONResponse({"status": "healthy"})


@app.post("/api/inference", response_model=InferenceResponse)
async def api_inference(req: InferenceRequest):
    """Run inference for a single test case."""
    full_prompt = (
        f"Task Context: {req.taskDescription}\n\n"
        f"Instruction: {req.promptTemplate}\n\n"
        f"Input: {req.query}"
    )
    messages = [{"role": "user", "content": full_prompt}]

    settings = None
    if req.settings:
        settings = LLMSettings(
            temperature=req.settings.get("temperature", 0.7),
            top_p=req.settings.get("topP"),
            top_k=req.settings.get("topK"),
        )

    model_id = _resolve_model(req.model)

    try:
        result = await generate(model=model_id, messages=messages, settings=settings)
        return InferenceResponse(output=result.content or "No response generated.")
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/jury", response_model=JuryResponse)
async def api_jury(req: JuryRequest):
    """Evaluate model output using a jury member."""
    system_prompt = get_prompt("jury")

    user_prompt = (
        f"TASK CONTEXT: {req.taskDescription}\n"
        f"USER QUERY: {req.row.query}\n"
        f"EXPECTED OUTPUT: {req.row.expectedOutput}\n"
        f"SOFT NEGATIVES: {req.row.softNegatives or 'None'}\n"
        f"HARD NEGATIVES: {req.row.hardNegatives or 'None'}\n\n"
        f'AI OUTPUT TO EVALUATE:\n"""\n{req.actualOutput}\n"""\n\n'
        'Return a JSON object with exactly two keys: '
        '"score" (number from 0 to 100) and "reasoning" (string with detailed critique). '
        "Be strict. If it hits a hard negative, score below 40."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    settings = None
    if req.jurySettings:
        settings = LLMSettings(
            temperature=req.jurySettings.get("temperature", 0),
            top_p=req.jurySettings.get("topP"),
            top_k=req.jurySettings.get("topK"),
        )

    model_id = _resolve_model(req.juryModel)

    try:
        result = await generate(
            model=model_id,
            messages=messages,
            settings=settings,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(result.content)
        return JuryResponse(
            score=float(parsed.get("score", 0)),
            reasoning=parsed.get("reasoning", "No reasoning provided."),
        )
    except (json.JSONDecodeError, KeyError):
        return JuryResponse(score=0, reasoning="Error parsing jury response.")
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))


REFINE_MODEL = "gemini/gemini-3-pro-preview"

@app.post("/api/refine", response_model=RefineResponse)
async def api_refine(req: RefineRequest):
    """Refine a prompt based on failure feedback."""
    system_prompt = get_prompt("rewriter")

    user_prompt = (
        f"TASK: {req.taskDescription}\n\n"
        f'CURRENT PROMPT:\n"""\n{req.currentPrompt}\n"""\n\n'
        f"CRITIQUE FROM FAILED TEST CASES (BACK-PROPAGATED ERROR):\n{req.failures}\n\n"
        "Return a JSON object with exactly three keys: "
        '"explanation" (string), "refinedPrompt" (string), "deltaReasoning" (string).'
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    settings = LLMSettings(temperature=0.2)

    try:
        result = await generate(
            model=REFINE_MODEL,
            messages=messages,
            settings=settings,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(result.content)
        return RefineResponse(
            explanation=parsed.get("explanation", "Failed to refine."),
            refinedPrompt=parsed.get("refinedPrompt", req.currentPrompt),
            deltaReasoning=parsed.get("deltaReasoning", "None"),
        )
    except (json.JSONDecodeError, KeyError):
        return RefineResponse(
            explanation="Failed to refine.",
            refinedPrompt=req.currentPrompt,
            deltaReasoning="None",
        )
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------

@app.post("/api/metrics", response_model=MetricsResponse)
def log_iteration_metrics(req: MetricsRequest):
    """Compute and log metrics for a completed jury evaluation round.

    Computes traditional + non-traditional metrics from jury results,
    then logs them to MLflow along with the prompt version and token usage.
    """
    results_dicts = [{"score": r.score, "reasoning": r.reasoning} for r in req.results]
    metrics = compute_metrics(results_dicts)

    run_id = mlflow_register(
        experiment_name=req.experimentId,
        metrics_dict=metrics,
        iteration=req.iteration,
        prompt_text=req.promptText,
        token_usage=req.tokenUsage,
        run_name=f"iteration-{req.iteration}",
    )

    return MetricsResponse(metrics=metrics, mlflowRunId=run_id)


# ---------------------------------------------------------------------------
# Dataset endpoints
# ---------------------------------------------------------------------------

@app.post("/api/dataset", response_model=DatasetUploadResponse)
def upload_dataset(req: DatasetUploadRequest, db: Session = Depends(get_db)):
    """Upload dataset rows for an experiment.

    Rows can have pre-assigned splits (train/val/test) or be auto-split
    using the provided ratios (default 70/15/15).
    """
    experiment = db.query(Experiment).filter(Experiment.id == req.experimentId).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found.")

    rows = list(req.rows)

    if req.autoSplit:
        # Assign splits to rows that don't already have one
        unassigned = [r for r in rows if r.split is None]
        random.shuffle(unassigned)
        n = len(unassigned)
        n_train = round(n * req.trainRatio)
        n_val = round(n * req.valRatio)
        for i, row in enumerate(unassigned):
            if i < n_train:
                row.split = "train"
            elif i < n_train + n_val:
                row.split = "val"
            else:
                row.split = "test"

    db_rows = []
    for row in rows:
        db_row = DatasetRow(
            experiment_id=req.experimentId,
            split=row.split or "train",
            query=row.query,
            expected_output=row.expectedOutput,
            soft_negatives=row.softNegatives,
            hard_negatives=row.hardNegatives,
        )
        db.add(db_row)
        db_rows.append(db_row)

    db.commit()
    for r in db_rows:
        db.refresh(r)

    splits = _count_splits(db, req.experimentId)
    return DatasetUploadResponse(
        experimentId=req.experimentId,
        splits=splits,
        rowIds=[r.id for r in db_rows],
    )


@app.get("/api/dataset/{experiment_id}", response_model=SplitStats)
def get_dataset_stats(experiment_id: str, db: Session = Depends(get_db)):
    """Return split statistics for an experiment's dataset."""
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return _count_splits(db, experiment_id)


@app.get("/api/dataset/{experiment_id}/{split}")
def get_dataset_split(
    experiment_id: str,
    split: Literal["train", "val", "test"],
    db: Session = Depends(get_db),
):
    """Return all rows for a specific split of an experiment's dataset."""
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found.")

    rows = (
        db.query(DatasetRow)
        .filter(DatasetRow.experiment_id == experiment_id, DatasetRow.split == split)
        .all()
    )
    return [
        {
            "id": r.id,
            "query": r.query,
            "expectedOutput": r.expected_output,
            "softNegatives": r.soft_negatives,
            "hardNegatives": r.hard_negatives,
            "split": r.split,
        }
        for r in rows
    ]


def _count_splits(db: Session, experiment_id: str) -> SplitStats:
    """Count rows per split for an experiment."""
    rows = db.query(DatasetRow).filter(DatasetRow.experiment_id == experiment_id).all()
    counts = {"train": 0, "val": 0, "test": 0}
    for r in rows:
        if r.split in counts:
            counts[r.split] += 1
    return SplitStats(
        train=counts["train"],
        val=counts["val"],
        test=counts["test"],
        total=sum(counts.values()),
    )


# ---------------------------------------------------------------------------
# Models endpoint
# ---------------------------------------------------------------------------

@app.get("/api/models")
async def api_models(refresh: bool = False):
    """Return available LLM models grouped by provider."""
    return await get_available_models(force_refresh=refresh)


# ---------------------------------------------------------------------------
# Optimization endpoint (SSE streaming)
# ---------------------------------------------------------------------------

@app.post("/api/optimize")
async def api_optimize(req: OptimizeRequest):
    """Start an optimization loop and stream progress via SSE."""
    return optimize_endpoint(req)


# ---------------------------------------------------------------------------
# Placeholder endpoints (future implementation)
# ---------------------------------------------------------------------------

@app.get("/jury")
def jury(experiment_id: str, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="Jury processing not implemented yet.")

@app.get("/evaluate")
def evaluate(experiment_id: str, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="Evaluation processing not implemented yet.")

@app.get("/evaluation_metrics")
def evaluation_metrics(experiment_id: str, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="Evaluation metrics processing not implemented yet.")
