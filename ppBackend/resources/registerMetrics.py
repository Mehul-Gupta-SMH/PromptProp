"""
MLflow experiment tracking for PromptProp.

Logs per-iteration metrics, prompt versions as artifacts, and token usage.
"""

import logging
import os
import tempfile

import mlflow

logger = logging.getLogger(__name__)

_configured = False


def configure(tracking_uri: str | None = None) -> None:
    """Set the MLflow tracking URI. Call once at startup."""
    global _configured
    if _configured:
        return

    uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "sqlite:///./mlflow_dev.db")
    mlflow.set_tracking_uri(uri)
    logger.info(f"MLflow tracking URI set to: {uri}")
    _configured = True


def register(
    experiment_name: str,
    metrics_dict: dict,
    iteration: int | None = None,
    prompt_text: str | None = None,
    token_usage: dict | None = None,
    run_name: str | None = None,
) -> str | None:
    """Log metrics for one iteration to MLflow.

    Args:
        experiment_name: MLflow experiment name (typically the PromptProp experiment ID).
        metrics_dict: Flat dict of metric_name -> float from generateMetrics.compute_metrics().
        iteration: Iteration number (used as the MLflow step parameter).
        prompt_text: If provided, logged as a text artifact.
        token_usage: Optional dict with prompt_tokens, completion_tokens, total_tokens.
        run_name: Optional human-readable run name.

    Returns:
        The MLflow run ID, or None if logging failed.
    """
    configure()

    try:
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run(run_name=run_name) as run:
            step = iteration or 0

            # Log all computed metrics
            for name, value in metrics_dict.items():
                mlflow.log_metric(name, float(value), step=step)

            # Log token usage as separate metrics
            if token_usage:
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    if key in token_usage:
                        mlflow.log_metric(key, float(token_usage[key]), step=step)

            # Log iteration number as a param for easy filtering
            if iteration is not None:
                mlflow.log_param("iteration", iteration)

            # Log prompt version as a text artifact
            if prompt_text:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False, prefix=f"prompt_v{step}_"
                ) as f:
                    f.write(prompt_text)
                    tmp_path = f.name
                try:
                    mlflow.log_artifact(tmp_path, artifact_path="prompts")
                finally:
                    os.unlink(tmp_path)

            return run.info.run_id

    except Exception:
        logger.exception("Failed to log metrics to MLflow")
        return None
