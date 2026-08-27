# evals/schemas.py

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCriterion(BaseModel):
    """
    One acceptance criterion for an evaluation case.
    """

    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    description: str
    weight: float = Field(gt=0, le=1)
    evaluation_type: Literal["rule", "llm"]


class EvaluationCase(BaseModel):
    """
    A single evaluation case.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    task: Literal["task1", "task2"]
    name: str
    description: str

    input_data: dict[str, Any]

    criteria: list[EvaluationCriterion]

    adversarial: bool = False


class CriterionResult(BaseModel):
    """
    Result for one criterion.
    """

    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    score: float = Field(
        ge=0.0,
        le=1.0,
    )
    passed: bool
    method: Literal["rule", "llm"]
    reasoning: str = ""


class EvaluationCaseResult(BaseModel):
    """
    Result for one evaluation case.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    task: Literal["task1", "task2"]
    name: str
    adversarial: bool

    status: Literal["PASS", "FAIL", "ERROR"]

    quality_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    rule_score: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
    )

    judge_score: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
    )

    criteria: list[CriterionResult]

    latency_seconds: float | None = None

    actual_output: Any = None

    expected_facts: Any = None

    error: str | None = None


class EvaluationSummary(BaseModel):
    """
    Aggregate evaluation summary.
    """

    model_config = ConfigDict(extra="forbid")

    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int

    pass_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    average_quality_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    task1_average_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    task2_average_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    quality_gate_passed: bool


class EvaluationReport(BaseModel):
    """
    Complete evaluation report.
    """

    model_config = ConfigDict(extra="forbid")

    summary: EvaluationSummary
    results: list[EvaluationCaseResult]