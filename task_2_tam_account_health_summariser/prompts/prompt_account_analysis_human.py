
# =============================================================================
# Prompt 1 — Account Health Analysis
# =============================================================================

VERSION = "1.0.0"

ACCOUNT_ANALYSIS_HUMAN_PROMPT = """
Analyze the following account context.

================ ACCOUNT =================

{account}

================ DETERMINISTIC METRICS =================

{metrics}

================ LAST {days} DAYS OF TICKETS =================

{tickets}

================ TASK =================

Produce a structured account-health analysis.

Focus on:
- overall account situation
- positive signals
- negative signals
- important observations
- relationships between account health and recent support activity

Remember:
- Use only the supplied data.
- Do not invent facts.
- Do not calculate metrics that are already supplied differently.
- Do not make a churn claim unless the supplied evidence supports it.
- Do not produce the final TAM brief yet.
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

