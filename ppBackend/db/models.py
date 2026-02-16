"""
SQLAlchemy ORM models for PromptProp.

Schema is intentionally denormalized in a few places (e.g., storing
model_settings as JSON) to keep queries simple for a dev tool.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer,
    String, Text, JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------

class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    base_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    runner_model: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    dataset_rows: Mapped[list["DatasetRow"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    jury_members: Mapped[list["JuryMember"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    prompt_versions: Mapped[list["PromptVersion"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan",
        order_by="PromptVersion.iteration_number",
    )


# ---------------------------------------------------------------------------
# DatasetRow
# ---------------------------------------------------------------------------

class DatasetRow(Base):
    __tablename__ = "dataset_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    split: Mapped[str] = mapped_column(String(10), nullable=False, default="train")
    query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    soft_negatives: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hard_negatives: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    experiment: Mapped["Experiment"] = relationship(back_populates="dataset_rows")
    iteration_results: Mapped[list["IterationResult"]] = relationship(
        back_populates="dataset_row", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# JuryMember
# ---------------------------------------------------------------------------

class JuryMember(Base):
    __tablename__ = "jury_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    experiment: Mapped["Experiment"] = relationship(back_populates="jury_members")
    evaluations: Mapped[list["JuryEvaluation"]] = relationship(
        back_populates="jury_member", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# PromptVersion
# ---------------------------------------------------------------------------

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    iteration_number: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    average_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    refinement_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refinement_meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    experiment: Mapped["Experiment"] = relationship(back_populates="prompt_versions")
    iteration_results: Mapped[list["IterationResult"]] = relationship(
        back_populates="prompt_version", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# IterationResult
# ---------------------------------------------------------------------------

class IterationResult(Base):
    __tablename__ = "iteration_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    prompt_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("prompt_versions.id", ondelete="CASCADE"), nullable=False
    )
    dataset_row_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dataset_rows.id", ondelete="CASCADE"), nullable=False
    )
    actual_output: Mapped[str] = mapped_column(Text, nullable=False)
    average_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    combined_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    prompt_version: Mapped["PromptVersion"] = relationship(back_populates="iteration_results")
    dataset_row: Mapped["DatasetRow"] = relationship(back_populates="iteration_results")
    jury_evaluations: Mapped[list["JuryEvaluation"]] = relationship(
        back_populates="iteration_result", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# JuryEvaluation
# ---------------------------------------------------------------------------

class JuryEvaluation(Base):
    __tablename__ = "jury_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    iteration_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("iteration_results.id", ondelete="CASCADE"), nullable=False
    )
    jury_member_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jury_members.id", ondelete="CASCADE"), nullable=False
    )
    jury_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    iteration_result: Mapped["IterationResult"] = relationship(back_populates="jury_evaluations")
    jury_member: Mapped["JuryMember"] = relationship(back_populates="evaluations")
