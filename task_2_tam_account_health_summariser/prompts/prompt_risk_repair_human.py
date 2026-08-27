VERSION = "1.0.0"

RISK_REPAIR_HUMAN_PROMPT = """
The following risk analysis contains evidence that failed exact-match
validation.

================ ORIGINAL TICKETS =================

{tickets}

================ PREVIOUS RISK ANALYSIS =================

{risk_analysis}

================ VALIDATION ERRORS =================

{validation_errors}

================ TASK =================

Repair the risk analysis.

For every remaining risk:
- ticket_id must correspond to an original ticket
- evidence_quote must occur EXACTLY in that ticket's body
- risk_type must remain either Churn Risk or Escalation Signal
- severity must remain meaningful
- explanation must be supported by the ticket
- recommended_action must remain actionable

Do not invent new evidence.

If a risk cannot be supported by an exact quote from the original ticket,
remove that risk.
"""


CHANGELOG = [
    {
        "version": "1.0.0",
        "date": "2026-08-27",
        "changes": [
            "Initial prompt.",
        ],
    },
]