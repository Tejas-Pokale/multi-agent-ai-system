# evals/run_evals.py

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from task_3_evaluation_harness.evaluator import EvaluationHarness
from task_3_evaluation_harness.report import write_reports


def main() -> int:

    print(
        "\n"
        "============================================\n"
        " AI Evaluation Harness\n"
        "============================================\n"
    )

    print(
        "Running Task 1 and Task 2 evaluation cases...\n"
    )

    harness = EvaluationHarness()

    report = harness.run_all()

    json_path, markdown_path = (
        write_reports(
            report
        )
    )

    print(
        "\n"
        "============================================"
    )

    print(
        " Evaluation Summary"
    )

    print(
        "============================================"
    )

    print(
        f"Total tests:       "
        f"{report.summary.total_tests}"
    )

    print(
        f"Passed:            "
        f"{report.summary.passed_tests}"
    )

    print(
        f"Failed:            "
        f"{report.summary.failed_tests}"
    )

    print(
        f"Errors:            "
        f"{report.summary.error_tests}"
    )

    print(
        f"Overall score:     "
        f"{report.summary.average_quality_score:.3f}"
    )

    print(
        f"Task 1 score:      "
        f"{report.summary.task1_average_score:.3f}"
    )

    print(
        f"Task 2 score:      "
        f"{report.summary.task2_average_score:.3f}"
    )

    print(
        f"Pass rate:         "
        f"{report.summary.pass_rate:.1%}"
    )

    print(
        f"Quality gate:      "
        f"{'PASS' if report.summary.quality_gate_passed else 'FAIL'}"
    )

    print("")

    print(
        f"JSON report:       {json_path}"
    )

    print(
        f"Markdown report:   {markdown_path}"
    )

    print("")

    return (
        0
        if report.summary.quality_gate_passed
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )