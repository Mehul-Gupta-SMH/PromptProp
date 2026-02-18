"""Tests for experiment history endpoints."""

import pytest
from sqlalchemy.orm import sessionmaker

from db.models import (
    Experiment, DatasetRow, JuryMember, PromptVersion,
    IterationResult, JuryEvaluation,
)


@pytest.fixture()
def experiment_with_iterations(db_engine):
    """Create an experiment with prompt versions, results, and jury evaluations."""
    Session = sessionmaker(bind=db_engine)
    session = Session()

    exp = Experiment(
        task_description="Classify feedback",
        base_prompt="You are a classifier.",
        runner_model={"provider": "gemini", "model": "gemini-3-flash-preview"},
        is_complete=True,
    )
    session.add(exp)
    session.flush()

    # Dataset rows
    rows = []
    for i in range(2):
        row = DatasetRow(
            experiment_id=exp.id,
            split="train",
            query=f"feedback {i}",
            expected_output=f"category {i}",
        )
        session.add(row)
        rows.append(row)
    session.flush()

    # Jury member
    jm = JuryMember(
        experiment_id=exp.id,
        name="judge-1",
        provider="gemini",
        model="gemini-3-pro-preview",
        settings={"temperature": 0},
    )
    session.add(jm)
    session.flush()

    # Prompt versions with results
    for iter_num in range(1, 3):
        pv = PromptVersion(
            experiment_id=exp.id,
            iteration_number=iter_num,
            prompt_text=f"Prompt v{iter_num}",
            average_score=70.0 + iter_num * 10,
            refinement_feedback=f"Feedback for iter {iter_num}",
        )
        session.add(pv)
        session.flush()

        for row in rows:
            ir = IterationResult(
                prompt_version_id=pv.id,
                dataset_row_id=row.id,
                actual_output=f"output iter{iter_num} row{row.id}",
                average_score=70.0 + iter_num * 10,
            )
            session.add(ir)
            session.flush()

            je = JuryEvaluation(
                iteration_result_id=ir.id,
                jury_member_id=jm.id,
                jury_name=jm.name,
                score=70.0 + iter_num * 10,
                reasoning=f"reasoning iter{iter_num}",
            )
            session.add(je)

    session.commit()
    exp_id = exp.id
    session.expunge_all()
    session.close()
    return exp_id


class TestListExperiments:
    def test_empty_list(self, client):
        resp = client.get("/api/experiments")
        assert resp.status_code == 200
        body = resp.json()
        assert body["experiments"] == []
        assert body["total"] == 0

    def test_list_returns_experiment(self, client, experiment_with_iterations):
        resp = client.get("/api/experiments")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        exp = body["experiments"][0]
        assert exp["id"] == experiment_with_iterations
        assert exp["taskDescription"] == "Classify feedback"
        assert exp["iterationCount"] == 2
        assert exp["bestScore"] == 90.0
        assert exp["finalScore"] == 90.0
        assert exp["datasetSize"] == 2
        assert exp["isComplete"] is True

    def test_pagination(self, client, db_engine):
        Session = sessionmaker(bind=db_engine)
        session = Session()
        for i in range(5):
            session.add(Experiment(
                task_description=f"Task {i}",
                base_prompt="prompt",
                runner_model={},
            ))
        session.commit()
        session.close()

        resp = client.get("/api/experiments?limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5
        assert len(body["experiments"]) == 2

        resp2 = client.get("/api/experiments?limit=2&offset=2")
        body2 = resp2.json()
        assert len(body2["experiments"]) == 2

        # IDs should be different between pages
        ids1 = {e["id"] for e in body["experiments"]}
        ids2 = {e["id"] for e in body2["experiments"]}
        assert ids1.isdisjoint(ids2)


class TestGetExperimentDetail:
    def test_404_for_unknown_id(self, client):
        resp = client.get("/api/experiments/nonexistent-id")
        assert resp.status_code == 404

    def test_returns_full_nested_structure(self, client, experiment_with_iterations):
        resp = client.get(f"/api/experiments/{experiment_with_iterations}")
        assert resp.status_code == 200
        body = resp.json()

        assert body["id"] == experiment_with_iterations
        assert body["taskDescription"] == "Classify feedback"
        assert body["isComplete"] is True

        # Jury members
        assert len(body["juryMembers"]) == 1
        assert body["juryMembers"][0]["name"] == "judge-1"

        # Dataset rows
        assert len(body["datasetRows"]) == 2

        # Prompt versions
        assert len(body["promptVersions"]) == 2
        pv1, pv2 = body["promptVersions"]
        assert pv1["iterationNumber"] == 1
        assert pv2["iterationNumber"] == 2

        # Each prompt version has results
        assert len(pv1["results"]) == 2
        assert len(pv2["results"]) == 2

        # Each result has jury evaluations
        for result in pv1["results"]:
            assert len(result["juryEvaluations"]) == 1
            assert result["juryEvaluations"][0]["juryName"] == "judge-1"
            assert result["juryEvaluations"][0]["score"] == 80.0
