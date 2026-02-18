"""Shared test fixtures for PromptProp backend tests."""

import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure ppBackend is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.models import Base, Experiment, DatasetRow, JuryMember
from llm.models import GenerateResponse, TokenUsage


# ---------------------------------------------------------------------------
# Database fixtures (in-memory SQLite, shared connection via StaticPool)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_engine():
    """Create an in-memory SQLite engine with a single shared connection."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Yield a fresh DB session bound to the shared engine."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# FastAPI TestClient with DB override
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db_engine):
    """FastAPI TestClient with get_db overridden to use in-memory DB."""
    from starlette.testclient import TestClient
    from route import app
    from db.session import get_db

    Session = sessionmaker(bind=db_engine)

    def _override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# LLM / global state resets
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_llm_globals():
    """Reset _keys_configured between tests."""
    import llm.llm_client as _mod
    original = _mod._keys_configured
    _mod._keys_configured = False
    yield
    _mod._keys_configured = original


@pytest.fixture(autouse=True)
def reset_mlflow_globals():
    """Reset MLflow _configured between tests."""
    import resources.registerMetrics as _mod
    original = _mod._configured
    _mod._configured = False
    yield
    _mod._configured = original


@pytest.fixture()
def clear_prompt_cache():
    """Clear the lru_cache on get_prompt."""
    from prompts.getPrompt import get_prompt
    get_prompt.cache_clear()
    yield
    get_prompt.cache_clear()


@pytest.fixture()
def reset_models_cache():
    """Reset the models_list module cache."""
    import models_list as _mod
    old_cache, old_ts = _mod._cache, _mod._cache_ts
    _mod._cache = None
    _mod._cache_ts = 0
    yield
    _mod._cache, _mod._cache_ts = old_cache, old_ts


# ---------------------------------------------------------------------------
# Mock LLM helpers
# ---------------------------------------------------------------------------

def _make_mock_response(content="mock output", model="mock-model",
                        prompt_tokens=10, completion_tokens=20, total_tokens=30):
    """Build a mock litellm acompletion response (raw SDK format)."""
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], usage=usage, model=model)


def _make_generate_response(content="mock output", model="mock-model",
                            prompt_tokens=10, completion_tokens=20, total_tokens=30):
    """Build a GenerateResponse (what generate() returns after processing)."""
    return GenerateResponse(
        content=content,
        model=model,
        usage=TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )


@pytest.fixture()
def mock_litellm_response():
    """Factory fixture — call with kwargs to build a mock response."""
    return _make_mock_response


@pytest.fixture()
def mock_generate():
    """Patch litellm.acompletion with a default success response."""
    mock_resp = _make_mock_response()
    with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp) as m:
        yield m


@pytest.fixture()
def mock_mlflow():
    """Patch all mlflow calls to prevent disk writes."""
    with patch("resources.registerMetrics.mlflow") as m:
        mock_run = MagicMock()
        mock_run.info.run_id = "mock-run-id"
        m.start_run.return_value.__enter__ = MagicMock(return_value=mock_run)
        m.start_run.return_value.__exit__ = MagicMock(return_value=False)
        yield m


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_experiment(db_engine):
    """Insert and return a sample Experiment row via the shared engine."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    exp = Experiment(
        task_description="Test task",
        base_prompt="Test prompt",
        runner_model={"provider": "gemini", "model": "gemini-3-flash-preview"},
    )
    session.add(exp)
    session.commit()
    session.refresh(exp)
    # Expunge so the object is detached and can be used across sessions
    session.expunge(exp)
    session.close()
    return exp


@pytest.fixture()
def sample_experiment_with_data(db_engine, sample_experiment):
    """Insert experiment with dataset rows and jury members."""
    Session = sessionmaker(bind=db_engine)
    session = Session()

    for i in range(3):
        row = DatasetRow(
            experiment_id=sample_experiment.id,
            split="train",
            query=f"query {i}",
            expected_output=f"expected {i}",
        )
        session.add(row)

    jm = JuryMember(
        experiment_id=sample_experiment.id,
        name="judge-1",
        provider="gemini",
        model="gemini-3-flash-preview",
        settings={},
    )
    session.add(jm)
    session.commit()
    session.close()
    return sample_experiment
