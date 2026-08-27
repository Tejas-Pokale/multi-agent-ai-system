# evals/task2_runner.py

from __future__ import annotations

from datetime import date
from typing import Any

from task_2_tam_account_health_summariser.summary import summarize_account


def run_task2_case(
    input_data: dict[str, Any],
):
    """
    Execute Task 2 through the same Python function used by the application.
    """

    account_id = input_data["account_id"]

    days = int(
        input_data.get(
            "days",
            90,
        )
    )

    analysis_date = input_data.get(
        "analysis_date"
    )

    if isinstance(
        analysis_date,
        str,
    ):
        analysis_date = date.fromisoformat(
            analysis_date
        )

    return summarize_account(
        account_id=account_id,
        days=days,
        analysis_date=analysis_date,
    )