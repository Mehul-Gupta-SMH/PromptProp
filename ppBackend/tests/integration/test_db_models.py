"""Tests for SQLAlchemy ORM models and relationships."""

import pytest
from db.models import (
    Experiment, DatasetRow, JuryMember, PromptVersion,
    IterationResult, JuryEvaluation,
)


class TestExperiment:
    def test_create(self, db_session):
        exp = Experiment(
            task_description="Test",
            base_prompt="Prompt",
            runner_model={"model": "gpt-4o"},
        )
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)

        assert exp.id is not None
        assert len(exp.id) == 36  # UUID format
        assert exp.is_complete is False
        assert exp.created_at is not None

    def test_uuid_uniqueness(self, db_session):
        e1 = Experiment(task_description="T1", base_prompt="P1", runner_model={})
        e2 = Experiment(task_description="T2", base_prompt="P2", runner_model={})
        db_session.add_all([e1, e2])
        db_session.commit()
        assert e1.id != e2.id


class TestDatasetRow:
    def test_create_with_experiment(self, db_session, sample_experiment):
        row = DatasetRow(
            experiment_id=sample_experiment.id,
            split="train",
            query="What is 2+2?",
            expected_output="4",
        )
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)

        assert row.id is not None
        assert row.split == "train"
        assert row.experiment_id == sample_experiment.id

    def test_default_split(self, db_session, sample_experiment):
        row = DatasetRow(
            experiment_id=sample_experiment.id,
            query="q",
            expected_output="e",
        )
        db_session.add(row)
        db_session.commit()
        assert row.split == "train"


class TestJuryMember:
    def test_create(self, db_session, sample_experiment):
        jm = JuryMember(
            experiment_id=sample_experiment.id,
            name="Strict Judge",
            provider="openai",
            model="gpt-4o",
            settings={"temperature": 0},
        )
        db_session.add(jm)
        db_session.commit()
        db_session.refresh(jm)
        assert jm.id is not None
        assert jm.settings == {"temperature": 0}


class TestPromptVersion:
    def test_create(self, db_session, sample_experiment):
        pv = PromptVersion(
            experiment_id=sample_experiment.id,
            iteration_number=1,
            prompt_text="First version",
        )
        db_session.add(pv)
        db_session.commit()
        db_session.refresh(pv)
        assert pv.average_score is None
        assert pv.refinement_feedback is None


class TestIterationResult:
    def test_create_with_relationships(self, db_session, sample_experiment):
        row = DatasetRow(
            experiment_id=sample_experiment.id, query="q", expected_output="e"
        )
        pv = PromptVersion(
            experiment_id=sample_experiment.id, iteration_number=1, prompt_text="p"
        )
        db_session.add_all([row, pv])
        db_session.flush()

        ir = IterationResult(
            prompt_version_id=pv.id,
            dataset_row_id=row.id,
            actual_output="output",
            average_score=85.0,
        )
        db_session.add(ir)
        db_session.commit()
        db_session.refresh(ir)
        assert ir.id is not None
        assert ir.average_score == 85.0


class TestJuryEvaluation:
    def test_create(self, db_session, sample_experiment):
        row = DatasetRow(
            experiment_id=sample_experiment.id, query="q", expected_output="e"
        )
        pv = PromptVersion(
            experiment_id=sample_experiment.id, iteration_number=1, prompt_text="p"
        )
        jm = JuryMember(
            experiment_id=sample_experiment.id, name="j", provider="gemini",
            model="m", settings={}
        )
        db_session.add_all([row, pv, jm])
        db_session.flush()

        ir = IterationResult(
            prompt_version_id=pv.id, dataset_row_id=row.id, actual_output="o"
        )
        db_session.add(ir)
        db_session.flush()

        je = JuryEvaluation(
            iteration_result_id=ir.id,
            jury_member_id=jm.id,
            jury_name="j",
            score=92.5,
            reasoning="Well done",
        )
        db_session.add(je)
        db_session.commit()
        db_session.refresh(je)
        assert je.score == 92.5


class TestCascadeDelete:
    def test_delete_experiment_cascades(self, db_session, sample_experiment):
        # Re-load the experiment into this session
        exp = db_session.get(Experiment, sample_experiment.id)

        row = DatasetRow(
            experiment_id=exp.id, query="q", expected_output="e"
        )
        jm = JuryMember(
            experiment_id=exp.id, name="j", provider="g", model="m", settings={}
        )
        pv = PromptVersion(
            experiment_id=exp.id, iteration_number=1, prompt_text="p"
        )
        db_session.add_all([row, jm, pv])
        db_session.flush()

        ir = IterationResult(
            prompt_version_id=pv.id, dataset_row_id=row.id, actual_output="o"
        )
        db_session.add(ir)
        db_session.flush()

        je = JuryEvaluation(
            iteration_result_id=ir.id, jury_member_id=jm.id,
            jury_name="j", score=90, reasoning="r"
        )
        db_session.add(je)
        db_session.commit()

        # Delete experiment — everything should cascade
        db_session.delete(exp)
        db_session.commit()

        assert db_session.query(DatasetRow).count() == 0
        assert db_session.query(JuryMember).count() == 0
        assert db_session.query(PromptVersion).count() == 0
        assert db_session.query(IterationResult).count() == 0
        assert db_session.query(JuryEvaluation).count() == 0


class TestRelationships:
    def test_experiment_has_rows(self, db_session, sample_experiment_with_data):
        exp = db_session.get(Experiment, sample_experiment_with_data.id)
        assert len(exp.dataset_rows) == 3

    def test_experiment_has_jury(self, db_session, sample_experiment_with_data):
        exp = db_session.get(Experiment, sample_experiment_with_data.id)
        assert len(exp.jury_members) == 1
