# evals/report.py

from __future__ import annotations

import json
from pathlib import Path

from task_3_evaluation_harness.schemas import EvaluationReport


REPORT_DIR = (
    Path(__file__).resolve().parent.parent
    / "reports"
)


def write_reports(
    report: EvaluationReport,
) -> tuple[Path, Path]:

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = (
        REPORT_DIR
        / "eval_report.json"
    )

    markdown_path = (
        REPORT_DIR
        / "eval_report.md"
    )

    json_path.write_text(
        json.dumps(
            report.model_dump(
                mode="json"
            ),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    markdown_path.write_text(
        build_markdown_report(
            report
        ),
        encoding="utf-8",
    )

    return (
        json_path,
        markdown_path,
    )


def build_markdown_report(
    report: EvaluationReport,
) -> str:

    summary = report.summary

    lines: list[str] = []

    lines.append(
        "# AI Evaluation Report"
    )

    lines.append("")
    lines.append(
        "## Overall Summary"
    )
    lines.append("")

    lines.append(
        "| Metric | Result |"
    )
    lines.append(
        "|---|---:|"
    )

    lines.append(
        f"| Total tests | {summary.total_tests} |"
    )

    lines.append(
        f"| Passed | {summary.passed_tests} |"
    )

    lines.append(
        f"| Failed | {summary.failed_tests} |"
    )

    lines.append(
        f"| Errors | {summary.error_tests} |"
    )

    lines.append(
        f"| Pass rate | {summary.pass_rate:.1%} |"
    )

    lines.append(
        f"| Overall quality | "
        f"{summary.average_quality_score:.3f} |"
    )

    lines.append(
        f"| Task 1 average | "
        f"{summary.task1_average_score:.3f} |"
    )

    lines.append(
        f"| Task 2 average | "
        f"{summary.task2_average_score:.3f} |"
    )

    lines.append(
        f"| Quality gate | "
        f"{'PASS' if summary.quality_gate_passed else 'FAIL'} |"
    )

    lines.append("")

    # -------------------------------------------------------------------------
    # Task tables
    # -------------------------------------------------------------------------

    for task_name, task_id in [
        ("Task 1", "task1"),
        ("Task 2", "task2"),
    ]:

        lines.append(
            f"## {task_name}"
        )

        lines.append("")

        lines.append(
            "| ID | Test | Adversarial | Rule | "
            "Judge | Overall | Status | Latency |"
        )

        lines.append(
            "|---|---|---|---:|---:|---:|---|---:|"
        )

        task_results = [
            result
            for result in report.results
            if result.task == task_id
        ]

        for result in task_results:

            adversarial = (
                "Yes"
                if result.adversarial
                else "No"
            )

            latency = (
                f"{result.latency_seconds:.2f}s"
                if result.latency_seconds is not None
                else "—"
            )

            lines.append(
                f"| {result.case_id} "
                f"| {result.name} "
                f"| {adversarial} "
                f"| {result.rule_score:.3f} "
                f"| {result.judge_score:.3f} "
                f"| {result.quality_score:.3f} "
                f"| {result.status} "
                f"| {latency} |"
            )

        lines.append("")

    # -------------------------------------------------------------------------
    # Detailed criteria
    # -------------------------------------------------------------------------

    lines.append(
        "## Detailed Results"
    )

    lines.append("")

    for result in report.results:

        lines.append(
            f"### {result.case_id} — {result.name}"
        )

        lines.append("")

        lines.append(
            f"**Status:** {result.status}"
        )

        lines.append(
            f"**Quality score:** "
            f"{result.quality_score:.3f}"
        )

        lines.append(
            f"**Rule score:** "
            f"{result.rule_score:.3f}"
        )

        lines.append(
            f"**LLM judge score:** "
            f"{result.judge_score:.3f}"
        )

        if result.error:

            lines.append("")

            lines.append(
                f"**Error:** {result.error}"
            )

            lines.append("")

            continue

        lines.append("")

        lines.append(
            "| Criterion | Method | Score | "
            "Result | Reasoning |"
        )

        lines.append(
            "|---|---|---:|---|---|"
        )

        for criterion in result.criteria:

            result_label = (
                "PASS"
                if criterion.passed
                else "FAIL"
            )

            reasoning = (
                criterion.reasoning
                .replace("|", "/")
                .replace("\n", " ")
            )

            lines.append(
                f"| {criterion.criterion_id} "
                f"| {criterion.method} "
                f"| {criterion.score:.3f} "
                f"| {result_label} "
                f"| {reasoning} |"
            )

        lines.append("")

    return "\n".join(
        lines
    )