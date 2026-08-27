
VERSION = "1.0.0"

RISK_DETECTION_HUMAN_PROMPT = """
Detect churn risks and escalation signals in the following account and ticket
context.

================ ACCOUNT =================

{account}

================ ACCOUNT ANALYSIS =================

{account_analysis}

================ DETERMINISTIC METRICS =================

{metrics}

================ TICKETS =================

{tickets}

================ TASK =================

Review every supplied ticket.

For each ticket, decide whether it contains meaningful evidence of:

- Churn Risk
- Escalation Signal

Only flag a ticket when the evidence supports the classification.

For every flag:
1. Use the correct ticket_id.
2. Select the appropriate risk_type.
3. Assign a reasonable severity.
4. Copy an EXACT quote from that ticket's body into evidence_quote.
5. Explain why the quote represents the risk.
6. Give a concise recommended TAM action.

IMPORTANT:

The evidence_quote MUST appear verbatim in the corresponding ticket body.

Do not invent quotes.
Do not paraphrase quotes.
Do not use evidence from another ticket.
Do not use account-level information as the ticket quote.

If no ticket contains a meaningful churn or escalation signal, return an
empty list of flags.
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
