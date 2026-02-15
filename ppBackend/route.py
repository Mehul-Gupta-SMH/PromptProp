import json
import logging

import fastapi
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from llm import generate, ModelSettings as LLMSettings, LLMError

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
    jury_prompt = (
        f"TASK CONTEXT: {req.taskDescription}\n"
        f"USER QUERY: {req.row.query}\n"
        f"EXPECTED OUTPUT: {req.row.expectedOutput}\n"
        f"SOFT NEGATIVES: {req.row.softNegatives or 'None'}\n"
        f"HARD NEGATIVES: {req.row.hardNegatives or 'None'}\n\n"
        f'AI OUTPUT TO EVALUATE:\n"""\n{req.actualOutput}\n"""\n\n'
        "Evaluate the AI output objectively based on the criteria. "
        'Return a JSON object with exactly two keys: '
        '"score" (number from 0 to 100) and "reasoning" (string with detailed critique). '
        "Be strict. If it hits a hard negative, score below 40."
    )
    messages = [{"role": "user", "content": jury_prompt}]

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
    refiner_prompt = (
        "You are a Prompt Meta-Optimizer.\n"
        f"TASK: {req.taskDescription}\n\n"
        f'CURRENT PROMPT:\n"""\n{req.currentPrompt}\n"""\n\n'
        f"CRITIQUE FROM FAILED TEST CASES (BACK-PROPAGATED ERROR):\n{req.failures}\n\n"
        "INSTRUCTIONS:\n"
        "1. Identify exactly where the current prompt fails to guide the model.\n"
        "2. Rewrite the prompt to fix these specific issues.\n"
        "3. Keep existing successes intact.\n"
        '4. Provide a "deltaReasoning" explaining why this change specifically targets the observed failures.\n\n'
        "Return a JSON object with exactly three keys: "
        '"explanation" (string), "refinedPrompt" (string), "deltaReasoning" (string).'
    )
    messages = [{"role": "user", "content": refiner_prompt}]
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
# Placeholder endpoints (future implementation)
# ---------------------------------------------------------------------------

@app.get("/jury")
async def jury(agent_config: dict, generated_answer: dict, reference_answer: dict, experiment_id: str):
    raise HTTPException(status_code=501, detail="Jury processing not implemented yet.")

@app.get("/evaluate")
async def evaluate(agent_config: dict, jury_eval: dict, experiment_id: str):
    raise HTTPException(status_code=501, detail="Evaluation processing not implemented yet.")

@app.get("/evaluation_metrics")
async def evaluation_metrics(experiment_id: str):
    raise HTTPException(status_code=501, detail="Evaluation metrics processing not implemented yet.")

@app.post("/train_data")
async def train_data(experiment_id: str, data: dict):
    raise HTTPException(status_code=501, detail="Training data processing not implemented yet.")

@app.post("/validation_data")
async def validation_data(experiment_id: str, data: dict):
    raise HTTPException(status_code=501, detail="Validation data processing not implemented yet.")

@app.post("/test_data")
async def test_data(experiment_id: str, data: dict):
    raise HTTPException(status_code=501, detail="Test data processing not implemented yet.")
