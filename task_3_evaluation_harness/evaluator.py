# evals/evaluator.py

from __future__ import annotations

from datetime import date
from typing import Any

from task_3_evaluation_harness.cases import ALL_CASES
from task_3_evaluation_harness.judge import EvaluationJudge
from task_3_evaluation_harness.rules import (
    check_task1_structured_output,
    check_task2_account_identity,
    check_task2_health_status,
    check_task2_metrics,
    check_task2_nonempty_output,
    check_task2_required_sections,
    check_task2_risk_evidence,
    check_task2_ticket_window,
    check_task2_usage_trend,
)
from task_3_evaluation_harness.schemas import (
    CriterionResult,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationReport,
    EvaluationSummary,
)
from task_3_evaluation_harness.task1_runner import run_task1_case
from task_3_evaluation_harness.task2_expectations import (
    build_task2_expectations,
)
from task_3_evaluation_harness.task2_runner import run_task2_case


# =============================================================================
# Quality gates
# =============================================================================

CASE_PASS_THRESHOLD = 0.75

TASK_PASS_THRESHOLD = 0.75

OVERALL_QUALITY_GATE = 0.80


class EvaluationHarness:

    def __init__(
        self,
        cases: list[EvaluationCase] | None = None,
    ) -> None:

        self.cases = (
            cases
            if cases is not None
            else ALL_CASES
        )

        self.judge = EvaluationJudge()

    # =========================================================================
    # Run all
    # =========================================================================

    def run_all(
        self,
    ) -> EvaluationReport:

        results: list[
            EvaluationCaseResult
        ] = []

        ordered_cases = sorted(
            self.cases,
            key=lambda case: case.case_id,
        )

        for case in ordered_cases:

            result = self.run_case(
                case
            )

            results.append(
                result
            )

            print(
                f"{case.case_id}: "
                f"{result.status} "
                f"{result.quality_score:.2f}"
            )

        return self._build_report(
            results
        )

    # =========================================================================
    # Run one case
    # =========================================================================

    def run_case(
        self,
        case: EvaluationCase,
    ) -> EvaluationCaseResult:

        output: Any = None
        expected_facts: Any = None
        latency: float | None = None

        try:

            # ---------------------------------------------------------------
            # Build Task 2 ground truth directly from Task 2.
            # ---------------------------------------------------------------

            if case.task == "task2":

                expected_facts = (
                    self._build_task2_expectations(
                        case
                    )
                )

            # ---------------------------------------------------------------
            # Execute application.
            # ---------------------------------------------------------------

            if case.task == "task1":

                output, latency = (
                    run_task1_case(
                        case.input_data
                    )
                )

            else:

                output = run_task2_case(
                    case.input_data
                )

            # ---------------------------------------------------------------
            # Evaluate criteria.
            # ---------------------------------------------------------------

            criterion_results = (
                self._evaluate_criteria(
                    case=case,
                    output=output,
                    expected_facts=expected_facts,
                )
            )

            quality_score = (
                self._calculate_quality_score(
                    case=case,
                    criterion_results=criterion_results,
                )
            )

            rule_results = [
                result
                for result
                in criterion_results
                if result.method == "rule"
            ]

            judge_results = [
                result
                for result
                in criterion_results
                if result.method == "llm"
            ]

            rule_score = (
                self._average_score(
                    rule_results
                )
            )

            judge_score = (
                self._average_score(
                    judge_results
                )
            )

            status = (
                "PASS"
                if quality_score
                >= CASE_PASS_THRESHOLD
                else "FAIL"
            )

            return EvaluationCaseResult(
                case_id=case.case_id,
                task=case.task,
                name=case.name,
                adversarial=case.adversarial,
                status=status,
                quality_score=quality_score,
                rule_score=rule_score,
                judge_score=judge_score,
                criteria=criterion_results,
                latency_seconds=latency,
                actual_output=self._serialize(
                    output
                ),
                expected_facts=self._serialize(
                    expected_facts
                ),
            )

        except Exception as exc:

            print(f'Error Occured : {exc}')

            return EvaluationCaseResult(
                case_id=case.case_id,
                task=case.task,
                name=case.name,
                adversarial=case.adversarial,
                status="ERROR",
                quality_score=0.0,
                rule_score=0.0,
                judge_score=0.0,
                criteria=[],
                latency_seconds=latency,
                actual_output=None,
                expected_facts=(
                    self._serialize(
                        expected_facts
                    )
                ),
                error=str(exc),
            )

    # =========================================================================
    # Ground truth
    # =========================================================================

    @staticmethod
    def _build_task2_expectations(
        case: EvaluationCase,
    ) -> dict[str, Any]:

        account_id = case.input_data[
            "account_id"
        ]

        days = int(
            case.input_data.get(
                "days",
                90,
            )
        )

        analysis_date = (
            case.input_data.get(
                "analysis_date"
            )
        )

        if isinstance(
            analysis_date,
            str,
        ):

            analysis_date = date.fromisoformat(
                analysis_date
            )

        if not isinstance(
            analysis_date,
            date,
        ):

            raise ValueError(
                "Task 2 evaluation case must have "
                "a valid analysis_date."
            )

        return build_task2_expectations(
            account_id=account_id,
            days=days,
            analysis_date=analysis_date,
        )

    # =========================================================================
    # Criteria
    # =========================================================================

    def _evaluate_criteria(
        self,
        case: EvaluationCase,
        output: Any,
        expected_facts: Any,
    ) -> list[CriterionResult]:

        results: list[
            CriterionResult
        ] = []

        for criterion in case.criteria:

            if criterion.evaluation_type == "rule":

                score, reasoning = (
                    self._run_rule(
                        case=case,
                        output=output,
                        expected_facts=expected_facts,
                        criterion_id=criterion.criterion_id,
                    )
                )

                results.append(
                    CriterionResult(
                        criterion_id=criterion.criterion_id,
                        score=score,
                        passed=(
                            score
                            >= CASE_PASS_THRESHOLD
                        ),
                        method="rule",
                        reasoning=reasoning,
                    )
                )

            else:

                judge_result = (
                    self.judge.evaluate(
                        task=case.task,
                        test_input=case.input_data,
                        expected_facts=expected_facts,
                        actual_output=output,
                        criterion=criterion.description,
                    )
                )

                results.append(
                    CriterionResult(
                        criterion_id=criterion.criterion_id,
                        score=judge_result.score,
                        passed=judge_result.passed,
                        method="llm",
                        reasoning=judge_result.reasoning,
                    )
                )

        return results

    # =========================================================================
    # Rule dispatcher
    # =========================================================================

    @staticmethod
    def _run_rule(
        case: EvaluationCase,
        output: Any,
        expected_facts: Any,
        criterion_id: str,
    ) -> tuple[float, str]:

        if case.task == "task1":

            if criterion_id == "structured_output":

                return (
                    check_task1_structured_output(
                        output
                    )
                )

            return (
                0.0,
                f"No Task 1 rule implemented for '{criterion_id}'.",
            )

        # ---------------------------------------------------------------------
        # Task 2
        # ---------------------------------------------------------------------

        if criterion_id == "account_identity":

            return check_task2_account_identity(
                output,
                expected_facts,
            )

        if criterion_id == "health_status":

            return check_task2_health_status(
                output,
                expected_facts,
            )

        if criterion_id == "usage_trend":

            return check_task2_usage_trend(
                output,
                expected_facts,
            )

        if criterion_id == "metrics":

            return check_task2_metrics(
                output,
                expected_facts,
            )

        if criterion_id == "ticket_window":

            return check_task2_ticket_window(
                output,
                expected_facts,
            )

        if criterion_id == "window_correctness":

            return check_task2_ticket_window(
                output,
                expected_facts,
            )

        if criterion_id == "risk_evidence":

            return check_task2_risk_evidence(
                output,
                expected_facts,
            )

        if criterion_id == "required_sections":

            return check_task2_required_sections(
                output
            )

        return check_task2_nonempty_output(
            output
        )

    # =========================================================================
    # Scoring
    # =========================================================================

    @staticmethod
    def _calculate_quality_score(
        case: EvaluationCase,
        criterion_results: list[CriterionResult],
    ) -> float:

        result_map = {
            result.criterion_id: result
            for result in criterion_results
        }

        numerator = 0.0
        denominator = 0.0

        for criterion in case.criteria:

            result = result_map.get(
                criterion.criterion_id
            )

            if result is None:
                continue

            numerator += (
                result.score
                * criterion.weight
            )

            denominator += (
                criterion.weight
            )

        if denominator == 0:
            return 0.0

        return round(
            numerator / denominator,
            4,
        )

    @staticmethod
    def _average_score(
        results: list[CriterionResult],
    ) -> float:

        if not results:
            return 0.0

        return round(
            sum(
                result.score
                for result in results
            )
            / len(results),
            4,
        )

    # =========================================================================
    # Aggregate report
    # =========================================================================

    @staticmethod
    def _build_report(
        results: list[EvaluationCaseResult],
    ) -> EvaluationReport:

        total = len(results)

        passed = sum(
            result.status == "PASS"
            for result in results
        )

        failed = sum(
            result.status == "FAIL"
            for result in results
        )

        errors = sum(
            result.status == "ERROR"
            for result in results
        )

        pass_rate = (
            passed / total
            if total
            else 0.0
        )

        valid_scores = [
            result.quality_score
            for result in results
            if result.status != "ERROR"
        ]

        average_score = (
            sum(valid_scores)
            / len(valid_scores)
            if valid_scores
            else 0.0
        )

        task1_scores = [
            result.quality_score
            for result in results
            if result.task == "task1"
            and result.status != "ERROR"
        ]

        task2_scores = [
            result.quality_score
            for result in results
            if result.task == "task2"
            and result.status != "ERROR"
        ]

        task1_average = (
            sum(task1_scores)
            / len(task1_scores)
            if task1_scores
            else 0.0
        )

        task2_average = (
            sum(task2_scores)
            / len(task2_scores)
            if task2_scores
            else 0.0
        )

        quality_gate_passed = (
            errors == 0
            and task1_average
            >= TASK_PASS_THRESHOLD
            and task2_average
            >= TASK_PASS_THRESHOLD
            and average_score
            >= OVERALL_QUALITY_GATE
        )

        summary = EvaluationSummary(
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            error_tests=errors,
            pass_rate=round(
                pass_rate,
                4,
            ),
            average_quality_score=round(
                average_score,
                4,
            ),
            task1_average_score=round(
                task1_average,
                4,
            ),
            task2_average_score=round(
                task2_average,
                4,
            ),
            quality_gate_passed=(
                quality_gate_passed
            ),
        )

        return EvaluationReport(
            summary=summary,
            results=results,
        )

    # =========================================================================
    # Serialization
    # =========================================================================

    @staticmethod
    def _serialize(
        output: Any,
    ) -> Any:

        if output is None:
            return None

        if hasattr(
            output,
            "model_dump",
        ):

            return output.model_dump(
                mode="json"
            )

        if isinstance(
            output,
            dict,
        ):

            return output

        return str(output)
