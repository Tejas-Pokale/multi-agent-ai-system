# evals/rules.py

from __future__ import annotations

from typing import Any


# =============================================================================
# Generic helpers
# =============================================================================

def get_nested(
    data: Any,
    path: str,
    default=None,
):
    """
    Safely retrieve a nested dictionary value.
    """

    current = data

    for key in path.split("."):

        if not isinstance(
            current,
            dict,
        ):
            return default

        current = current.get(
            key
        )

        if current is None:
            return default

    return current


def serialize_output(
    output: Any,
) -> Any:
    """
    Convert Pydantic output into JSON-compatible data.
    """

    if hasattr(
        output,
        "model_dump",
    ):
        return output.model_dump(
            mode="json"
        )

    return output


# =============================================================================
# Task 1
# =============================================================================

def check_task1_structured_output(
    output: dict[str, Any],
) -> tuple[float, str]:

    if not isinstance(
        output,
        dict,
    ):
        return (
            0.0,
            "Output is not a JSON object.",
        )

    expected_groups = [
        [
            "product_area",
            "productArea",
        ],
        [
            "issue_category",
            "issueCategory",
            "category",
        ],
        [
            "urgency",
            "urgency_tier",
        ],
        [
            "reasoning",
            "classification_reasoning",
        ],
        [
            "recommended_responder_team",
            "responder_team",
            "recommended_team",
        ],
        [
            "draft_first_response",
            "first_response",
            "draft_response",
        ],
    ]

    found = 0

    for aliases in expected_groups:

        if any(
            alias in output
            for alias in aliases
        ):
            found += 1

    score = (
        found
        / len(expected_groups)
    )

    return (
        score,
        f"Found {found}/{len(expected_groups)} expected output groups.",
    )


# =============================================================================
# Task 2
# =============================================================================

def get_task2_brief(
    output: Any,
) -> dict[str, Any]:

    data = serialize_output(
        output
    )

    if not isinstance(
        data,
        dict,
    ):
        return {}

    return data.get(
        "brief",
        data,
    )


def get_task2_account(
    output: Any,
) -> dict[str, Any]:

    data = serialize_output(
        output
    )

    if not isinstance(
        data,
        dict,
    ):
        return {}

    return data.get(
        "account",
        {},
    )


def get_task2_metrics(
    output: Any,
) -> dict[str, Any]:

    data = serialize_output(
        output
    )

    if not isinstance(
        data,
        dict,
    ):
        return {}

    return data.get(
        "metrics",
        {},
    )


def get_task2_risks(
    output: Any,
) -> list[dict[str, Any]]:

    brief = get_task2_brief(
        output
    )

    risks = brief.get(
        "open_risks",
        [],
    )

    return (
        risks
        if isinstance(risks, list)
        else []
    )


def check_task2_account_identity(
    output: Any,
    expected: dict[str, Any],
) -> tuple[float, str]:

    actual_account = get_task2_account(
        output
    )

    expected_account = expected[
        "account"
    ]

    checks = [
        (
            actual_account.get("account_id")
            == expected_account.get("account_id"),
            "account_id",
        ),
        (
            actual_account.get("company")
            == expected_account.get("company"),
            "company",
        ),
    ]

    passed = sum(
        result
        for result, _
        in checks
    )

    score = (
        passed
        / len(checks)
    )

    return (
        score,
        f"Matched {passed}/{len(checks)} account identity fields.",
    )


def check_task2_health_status(
    output: Any,
    expected: dict[str, Any],
) -> tuple[float, str]:

    actual = get_task2_account(
        output
    ).get(
        "health_status"
    )

    expected_value = expected[
        "account"
    ].get(
        "health_status"
    )

    # Pydantic enum is serialized to string.
    if hasattr(
        actual,
        "value",
    ):
        actual = actual.value

    if actual == expected_value:

        return (
            1.0,
            f"Health status matches: {expected_value}.",
        )

    return (
        0.0,
        f"Expected health status {expected_value}, got {actual}.",
    )


def check_task2_usage_trend(
    output: Any,
    expected: dict[str, Any],
) -> tuple[float, str]:

    actual = get_task2_account(
        output
    ).get(
        "usage_trend"
    )

    expected_value = expected[
        "account"
    ].get(
        "usage_trend"
    )

    if hasattr(
        actual,
        "value",
    ):
        actual = actual.value

    if actual == expected_value:

        return (
            1.0,
            f"Usage trend matches: {expected_value}.",
        )

    return (
        0.0,
        f"Expected usage trend {expected_value}, got {actual}.",
    )


def check_task2_metrics(
    output: Any,
    expected: dict[str, Any],
) -> tuple[float, str]:

    actual = get_task2_metrics(
        output
    )

    expected_metrics = expected[
        "metrics"
    ]

    fields = [
        "seat_utilization_percent",
        "licensed_seats",
        "active_seats",
        "tickets_last_90d",
        "open_tickets_last_90d",
        "p1_tickets_last_90d",
        "p2_tickets_last_90d",
        "average_ticket_satisfaction",
    ]

    matches = 0

    for field in fields:

        actual_value = actual.get(
            field
        )

        expected_value = expected_metrics.get(
            field
        )

        # Handle tiny float representation differences.
        if (
            isinstance(actual_value, float)
            and isinstance(expected_value, float)
        ):

            is_match = (
                abs(
                    actual_value
                    - expected_value
                )
                < 1e-6
            )

        else:

            is_match = (
                actual_value
                == expected_value
            )

        if is_match:
            matches += 1

    score = (
        matches
        / len(fields)
    )

    return (
        score,
        f"{matches}/{len(fields)} deterministic metrics match Task 2 data.",
    )


def check_task2_ticket_window(
    output: Any,
    expected: dict[str, Any],
) -> tuple[float, str]:

    expected_ticket_ids = set(
        expected[
            "ticket_ids"
        ]
    )

    risks = get_task2_risks(
        output
    )

    if not risks:

        if not expected_ticket_ids:
            return (
                1.0,
                "No recent tickets and no ticket-level risks.",
            )

        return (
            1.0,
            "No risks reference tickets outside the selected window.",
        )

    valid = 0

    for risk in risks:

        ticket_id = risk.get(
            "ticket_id"
        )

        if ticket_id in expected_ticket_ids:
            valid += 1

    score = (
        valid
        / len(risks)
    )

    return (
        score,
        f"{valid}/{len(risks)} risk tickets belong to the selected window.",
    )


def check_task2_risk_evidence(
    output: Any,
    expected: dict[str, Any],
) -> tuple[float, str]:

    risks = get_task2_risks(
        output
    )

    if not risks:

        return (
            1.0,
            "No risks were flagged.",
        )

    ticket_map = {
        ticket["ticket_id"]: ticket
        for ticket
        in expected["tickets"]
    }

    valid = 0

    for risk in risks:

        ticket_id = risk.get(
            "ticket_id"
        )

        quote = risk.get(
            "evidence_quote"
        )

        ticket = ticket_map.get(
            ticket_id
        )

        if (
            ticket
            and isinstance(
                quote,
                str,
            )
            and quote.strip()
            and quote in ticket.get(
                "body",
                "",
            )
        ):
            valid += 1

    score = (
        valid
        / len(risks)
    )

    return (
        score,
        f"{valid}/{len(risks)} risk quotes exactly match source ticket text.",
    )


def check_task2_required_sections(
    output: Any,
) -> tuple[float, str]:

    brief = get_task2_brief(
        output
    )

    checks = {
        "executive_summary": (
            "executive_summary"
            in brief
        ),
        "open_risks": (
            "open_risks"
            in brief
        ),
        "recommended_talking_points": (
            "recommended_talking_points"
            in brief
        ),
    }

    passed = sum(
        checks.values()
    )

    score = (
        passed
        / len(checks)
    )

    return (
        score,
        f"{passed}/3 required sections are present.",
    )


def check_task2_nonempty_output(
    output: Any,
) -> tuple[float, str]:

    if output is None:

        return (
            0.0,
            "Output is None.",
        )

    data = serialize_output(
        output
    )

    if not data:

        return (
            0.0,
            "Output is empty.",
        )

    return (
        1.0,
        "Output is non-empty.",
    )