"""
Run 3 text classification experiments through the /api/optimize SSE endpoint.

Usage:
    cd ppBackend
    python run_experiments.py

Requires: OPENAI_API_KEY set in environment (or .env file).
Server must be running on localhost:8000.
"""

import json
import sys
import time
import httpx

BASE_URL = "http://localhost:8000"

# ── Shared model config ────────────────────────────────────────────────────

RUNNER = {"provider": "openai", "model": "gpt-4o-mini", "settings": {"temperature": 0.3}}
JURY = [{"name": "Jury-1", "provider": "openai", "model": "gpt-4o-mini", "settings": {"temperature": 0}}]
MANAGER = {"model": "gpt-4o-mini", "settings": {"temperature": 0.2}}
SHARED = {
    "runnerModel": RUNNER,
    "juryMembers": JURY,
    "managerModel": MANAGER,
    "maxIterations": 3,
    "passThreshold": 90.0,
    "perfectScore": 98.0,
}

# ── Experiment definitions ─────────────────────────────────────────────────

EXPERIMENTS = [
    {
        "name": "Easy — Binary Sentiment",
        "taskDescription": "Classify the sentiment of the given text as exactly 'positive' or 'negative'. Output only the label, nothing else.",
        "basePrompt": "Read the text and classify it.",
        "dataset": [
            {"query": "This movie was amazing! Best film I've seen all year.", "expectedOutput": "positive"},
            {"query": "Terrible service, I will never come back.", "expectedOutput": "negative"},
            {"query": "I absolutely love this product, it changed my life!", "expectedOutput": "positive"},
        ],
    },
    {
        "name": "Medium — 4-Category Feedback",
        "taskDescription": "Classify customer feedback into exactly one category: 'Product', 'Billing', 'Shipping', or 'General'. Output only the category label.",
        "basePrompt": "Categorize this customer message.",
        "dataset": [
            {
                "query": "The widget broke after two days of normal use.",
                "expectedOutput": "Product",
                "softNegatives": "General",
            },
            {
                "query": "I was charged twice on my credit card for the same order.",
                "expectedOutput": "Billing",
                "softNegatives": "General",
            },
            {
                "query": "My package hasn't arrived and it's been 3 weeks.",
                "expectedOutput": "Shipping",
                "softNegatives": "General",
            },
            {
                "query": "How do I update my account email address?",
                "expectedOutput": "General",
                "softNegatives": "Billing",
            },
            {
                "query": "The item quality is poor and the color doesn't match the listing.",
                "expectedOutput": "Product",
                "softNegatives": "Shipping",
                "hardNegatives": "General",
            },
        ],
    },
    {
        "name": "Hard — 6-Category Intent Detection",
        "taskDescription": "Classify the support ticket intent as exactly one of: 'Purchase', 'Return', 'Complaint', 'Question', 'Compliment', or 'Other'. Output only the label.",
        "basePrompt": "What is the intent of this support message?",
        "dataset": [
            {
                "query": "I'd like to buy the premium plan for my team.",
                "expectedOutput": "Purchase",
                "softNegatives": "Question",
            },
            {
                "query": "This product is defective and I want my money back.",
                "expectedOutput": "Return",
                "softNegatives": "Complaint",
                "hardNegatives": "Purchase",
            },
            {
                "query": "Your support team was incredibly helpful, thank you!",
                "expectedOutput": "Compliment",
                "softNegatives": "Other",
            },
            {
                "query": "The app crashes every time I open it. This is unacceptable.",
                "expectedOutput": "Complaint",
                "softNegatives": "Return",
            },
            {
                "query": "What are the differences between the Basic and Pro plans?",
                "expectedOutput": "Question",
                "softNegatives": "Purchase",
            },
            {
                "query": "I bought this last week but want to return it for a different size.",
                "expectedOutput": "Return",
                "softNegatives": "Purchase",
                "hardNegatives": "Complaint",
            },
        ],
    },
]


# ── SSE streaming helper ──────────────────────────────────────────────────

def stream_experiment(exp_def: dict) -> dict:
    """POST to /api/optimize, stream SSE events, return final result."""
    payload = {**SHARED, **{k: v for k, v in exp_def.items() if k != "name"}}

    result = {"name": exp_def["name"], "experimentId": None, "iterations": 0, "finalScore": 0, "finalPrompt": ""}

    with httpx.Client(timeout=300) as client:
        with client.stream("POST", f"{BASE_URL}/api/optimize", json=payload) as resp:
            if resp.status_code != 200:
                print(f"  ERROR: HTTP {resp.status_code}")
                return result

            event_type = None
            data_buf = ""

            for line in resp.iter_lines():
                if line.startswith("event: "):
                    event_type = line[7:]
                    data_buf = ""
                elif line.startswith("data: "):
                    data_buf += line[6:]
                elif line == "" and event_type and data_buf:
                    data = json.loads(data_buf)
                    _handle_event(event_type, data, result)
                    event_type = None
                    data_buf = ""

    return result


def _handle_event(event: str, data: dict, result: dict):
    name = result["name"]

    if event == "start":
        result["experimentId"] = data["experimentId"]
        print(f"  Experiment ID: {data['experimentId']}")
        print(f"  Rows: {data['totalRows']}  |  Jury: {data['totalJury']}  |  Max iterations: {data['maxIterations']}")

    elif event == "iteration_start":
        print(f"\n  --- Iteration {data['iteration']} ---")
        prompt_preview = data["promptText"][:80].replace("\n", " ")
        print(f"  Prompt: {prompt_preview}...")

    elif event == "jury_result":
        scores = ", ".join(f"{s['juryName']}={s['score']}" for s in data["scores"])
        print(f"  Row {data['rowIndex']}: avg={data['averageScore']:.1f}  [{scores}]")

    elif event == "iteration_complete":
        avg = data["averageScore"]
        metrics = data.get("metrics", {})
        print(f"  >> Iteration avg: {avg}  |  pass_rate: {metrics.get('pass_rate', '?')}  |  converged: {data['converged']}")
        result["iterations"] = data["iteration"]
        result["finalScore"] = avg

    elif event == "refinement":
        expl = data.get("explanation", "")[:120].replace("\n", " ")
        print(f"  Refinement: {expl}")

    elif event == "complete":
        result["finalPrompt"] = data.get("finalPrompt", "")
        tokens = data.get("totalTokens", {})
        print(f"\n  COMPLETE — Final score: {data['finalScore']}  |  Iterations: {data['totalIterations']}")
        print(f"  Tokens — inference: {tokens.get('inference',0)}  jury: {tokens.get('jury',0)}  refine: {tokens.get('refinement',0)}  total: {tokens.get('total',0)}")

    elif event == "error":
        print(f"  ERROR [{data.get('stage')}]: {data.get('message')}")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    # Health check
    try:
        r = httpx.get(f"{BASE_URL}/health-check", timeout=5)
        r.raise_for_status()
        print("Server is healthy.\n")
    except Exception as e:
        print(f"Cannot reach server at {BASE_URL}: {e}")
        print("Start the server first:  cd ppBackend && python main.py")
        sys.exit(1)

    results = []

    for i, exp in enumerate(EXPERIMENTS, 1):
        print(f"\n{'='*60}")
        print(f"EXPERIMENT {i}/{len(EXPERIMENTS)}: {exp['name']}")
        print(f"{'='*60}")
        t0 = time.time()
        res = stream_experiment(exp)
        res["elapsed"] = round(time.time() - t0, 1)
        results.append(res)

    # Verify DB persistence
    print(f"\n\n{'='*60}")
    print("VERIFICATION: Querying /api/dataset for each experiment")
    print(f"{'='*60}")
    for res in results:
        eid = res.get("experimentId")
        if not eid:
            continue
        try:
            r = httpx.get(f"{BASE_URL}/api/dataset/{eid}", timeout=10)
            if r.status_code == 200:
                stats = r.json()
                print(f"  {res['name']}: {stats}")
            else:
                print(f"  {res['name']}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  {res['name']}: {e}")

    # Summary table
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Experiment':<35} {'Iters':>5} {'Score':>6} {'Time':>7}  {'ID'}")
    print(f"{'-'*35} {'-'*5} {'-'*6} {'-'*7}  {'-'*36}")
    for r in results:
        print(f"{r['name']:<35} {r['iterations']:>5} {r['finalScore']:>6.1f} {r['elapsed']:>6.1f}s  {r.get('experimentId', 'N/A')}")

    # Viewing instructions
    print(f"""
{'='*60}
HOW TO VIEW RESULTS
{'='*60}

A. SQLite Database:
   sqlite3 promptprop_dev.db
   SELECT id, task_description, is_complete FROM experiments;
   SELECT iteration_number, average_score, prompt_text FROM prompt_versions WHERE experiment_id = '<ID>';

B. MLflow UI:
   cd ppBackend
   mlflow ui --backend-store-uri sqlite:///./mlflow_dev.db
   Then visit http://localhost:5000
""")


if __name__ == "__main__":
    main()
