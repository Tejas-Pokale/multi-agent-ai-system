# evals/task2_expectations.py

from __future__ import annotations

from datetime import date
from typing import Any

from utils.get_data import (
    get_account_context,
)


def build_task2_expectations(
    account_id: str,
    days: int,
    analysis_date: date,
) -> dict[str, Any]:
    """
    Build factual expectations directly from Task 2's data layer.

    We deliberately do not duplicate facts from accounts.json or tickets.json
    inside the evaluation suite.

    Task 2's get_data.py remains the source of truth.
    """

    context = get_account_context(
        account_id=account_id,
        days=days,
        reference_date=analysis_date,
    )

    return {
        "account": context["account"],
        "metrics": context["metrics"],
        "tickets": context["tickets"],
        "ticket_ids": [
            ticket["ticket_id"]
            for ticket in context["tickets"]
        ],
        "ticket_count": len(
            context["tickets"]
        ),
    }