
VERSION = "1.0.0"

FINAL_BRIEF_HUMAN_PROMPT = """
Create the final TAM account brief from the following validated information.

================ ACCOUNT =================

{account}

================ DETERMINISTIC METRICS =================

{metrics}

================ ACCOUNT HEALTH ANALYSIS =================

{account_analysis}

================ VALIDATED RISK FINDINGS =================

{risk_analysis}

================ TASK =================

Produce the final structured TAM brief.

Requirements:

1. Executive summary:
   - exactly 3–5 sentences
   - concise
   - account-specific
   - evidence-based

2. Open risks & flagged issues:
   - include the validated risk findings
   - retain exact evidence quotes
   - do not invent additional risks
   - if no risks exist, explicitly indicate that no meaningful churn or
     escalation signals were identified

3. Recommended talking points:
   - actionable
   - account-specific
   - useful for a TAM/QBR conversation
   - include concrete customer questions

Do not introduce facts that are not contained in the supplied information.
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
