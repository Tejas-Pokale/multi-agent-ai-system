# evals/cases.py

from __future__ import annotations

from datetime import date

from task_3_evaluation_harness.schemas import (
    EvaluationCase,
    EvaluationCriterion,
)


# =============================================================================
# Task 1
# =============================================================================

TASK1_CASES = [

    EvaluationCase(
        case_id="T1-01",
        task="task1",
        name="Critical production failure",
        description=(
            "Clear production issue with significant user impact."
        ),
        input_data={
            "subject": (
                "Production pipeline failing for engineering users"
            ),
            "body": (
                "Our production DataBridge Pro pipeline has been failing "
                "since this morning. The error is occurring continuously "
                "and is affecting 75 users in Engineering. We have tried "
                "restarting the service but the issue persists. "
                "Please help urgently."
            ),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="product_area",
                description=(
                    "Product area should be consistent with the described "
                    "DataBridge Pro pipeline problem."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="category",
                description=(
                    "Issue category should represent a technical product "
                    "failure/bug rather than a feature request."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="urgency",
                description=(
                    "Urgency should appropriately reflect a continuously "
                    "failing production pipeline affecting 75 users."
                ),
                weight=0.25,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="reasoning",
                description=(
                    "Reasoning should mention production impact, affected "
                    "users, persistence of the problem, and urgency."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="response",
                description=(
                    "Draft response should acknowledge the impact and "
                    "request useful troubleshooting information."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
        ],
    ),

    EvaluationCase(
        case_id="T1-02",
        task="task1",
        name="Integration authentication failure",
        description="Clear third-party integration problem.",
        input_data={
            "subject": (
                "AnalyticsHub authentication failure with Azure AD"
            ),
            "body": (
                "We are integrating AnalyticsHub with Azure AD using the "
                "documented API approach, but authentication is failing. "
                "The OAuth token looks valid and the endpoint is reachable. "
                "Can you help identify the issue?"
            ),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="integration",
                description=(
                    "The output should recognize the problem as an "
                    "integration/authentication issue."
                ),
                weight=0.25,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="category",
                description=(
                    "The category should reasonably represent an "
                    "integration-related issue."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="urgency",
                description=(
                    "The output should not escalate to P1 solely because "
                    "authentication is failing; no critical business impact "
                    "is stated."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="reasoning",
                description=(
                    "Reasoning should use the Azure AD and OAuth evidence."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="response",
                description=(
                    "Draft response should be appropriate for diagnosing "
                    "an authentication/integration issue."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
        ],
    ),

    EvaluationCase(
        case_id="T1-03",
        task="task1",
        name="Routine feature request",
        description="Non-urgent feature request.",
        input_data={
            "subject": "Request for bulk archive operations",
            "body": (
                "We currently have to archive records one at a time. "
                "Our team would like the ability to select multiple records "
                "and archive them in one operation. The current workaround "
                "is manual and time-consuming."
            ),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="feature_request",
                description=(
                    "The ticket should be recognized as a feature request."
                ),
                weight=0.30,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="urgency",
                description=(
                    "The ticket should not be treated as a P1 critical "
                    "incident."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="reasoning",
                description=(
                    "Reasoning should recognize that the issue is an "
                    "inconvenient workflow rather than an outage."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="routing",
                description=(
                    "Suggested responder team should be relevant to "
                    "product/feature ownership."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="response",
                description=(
                    "Draft response should acknowledge the request without "
                    "claiming the feature already exists."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
        ],
    ),

    EvaluationCase(
        case_id="T1-04",
        task="task1",
        name="Data loss incident",
        description="Explicit missing-data scenario.",
        input_data={
            "subject": "Missing production records after sync failure",
            "body": (
                "Our CloudSync instance stopped syncing three days ago. "
                "We now have a discrepancy of approximately 5200 records "
                "and need help restoring synchronization and recovering "
                "the missing records. This affects a production workflow."
            ),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="category",
                description=(
                    "The output should identify the missing-data/data-loss "
                    "nature of the incident."
                ),
                weight=0.25,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="urgency",
                description=(
                    "Urgency should reflect production impact and missing "
                    "records."
                ),
                weight=0.25,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="reasoning",
                description=(
                    "Reasoning should explicitly connect missing records "
                    "and production impact to priority."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="routing",
                description=(
                    "Suggested responder team should be relevant to a "
                    "data/synchronization incident."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="response",
                description=(
                    "Draft response should acknowledge data impact and "
                    "prioritize recovery."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
        ],
    ),

    EvaluationCase(
        case_id="T1-05",
        task="task1",
        name="Ambiguous intermittent failure",
        description=(
            "Adversarial case containing business impact but insufficient "
            "evidence for an unquestionable P1."
        ),
        input_data={
            "subject": "AnalyticsHub exports intermittently failing",
            "body": (
                "Exports have been failing intermittently since yesterday. "
                "Some users can still complete exports, but our finance team "
                "is blocked on today's reporting deadline. No data has been "
                "lost. We need help determining whether this is a known issue."
            ),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="ambiguity_handling",
                description=(
                    "Reasoning should acknowledge the intermittent nature "
                    "of the failure."
                ),
                weight=0.25,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="no_data_loss",
                description=(
                    "The output must not incorrectly classify this as a "
                    "data-loss incident."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="urgency",
                description=(
                    "Urgency should recognize the reporting deadline without "
                    "blindly assuming a complete P1 outage."
                ),
                weight=0.25,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="reasoning",
                description=(
                    "Reasoning should explain the competing signals."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="response",
                description=(
                    "Draft response should acknowledge the deadline and "
                    "request useful diagnostics."
                ),
                weight=0.10,
                evaluation_type="llm",
            ),
        ],
        adversarial=True,
    ),

    EvaluationCase(
        case_id="T1-06",
        task="task1",
        name="Minimal incomplete ticket",
        description="Very little information is provided.",
        input_data={
            "subject": "It is broken",
            "body": "Please help. It stopped working.",
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="no_hallucination",
                description=(
                    "The output should not invent a product, error message, "
                    "environment, user count, or business impact."
                ),
                weight=0.30,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="uncertainty",
                description=(
                    "Reasoning should acknowledge insufficient information."
                ),
                weight=0.25,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="response",
                description=(
                    "Draft response should request the missing information "
                    "needed to triage the issue."
                ),
                weight=0.25,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="structured_output",
                description=(
                    "The endpoint should still return a structured "
                    "triage response."
                ),
                weight=0.20,
                evaluation_type="rule",
            ),
        ],
    ),
]



# =============================================================================
# Task 2 cases
# =============================================================================

TASK2_CASES = [

    EvaluationCase(
        case_id="T2-01",
        task="task2",
        name="Healthy account grounding",
        description=(
            "Normal account-health summary using a real dataset account."
        ),
        input_data={
            "account_id": "ACC-4516",
            "days": 90,
            "analysis_date": date(2026, 8, 27),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="account_identity",
                description=(
                    "The final brief should refer to the correct account "
                    "and company."
                ),
                weight=0.10,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="health_status",
                description=(
                    "The account health status should match the actual "
                    "account record."
                ),
                weight=0.15,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="usage_trend",
                description=(
                    "The usage trend should match the actual account record."
                ),
                weight=0.10,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="metrics",
                description=(
                    "Displayed account metrics should be grounded in the "
                    "actual Task 2 data layer."
                ),
                weight=0.15,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="summary_quality",
                description=(
                    "The executive summary should accurately and concisely "
                    "synthesize the account's situation."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="risk_quality",
                description=(
                    "Risk findings should be supported by the supplied "
                    "account and ticket evidence and should avoid invented "
                    "risk."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="talking_points",
                description=(
                    "Talking points should be useful and specific to this "
                    "account."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
        ],
    ),

    EvaluationCase(
        case_id="T2-02",
        task="task2",
        name="At-risk account grounding",
        description=(
            "Account with explicit negative health indicators."
        ),
        input_data={
            "account_id": "ACC-3930",
            "days": 90,
            "analysis_date": date(2026, 8, 27),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="account_identity",
                description=(
                    "The brief should refer to the correct account."
                ),
                weight=0.10,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="health_status",
                description=(
                    "The brief should correctly reflect the source "
                    "health status."
                ),
                weight=0.15,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="usage_trend",
                description=(
                    "The brief should correctly reflect the source "
                    "usage trend."
                ),
                weight=0.10,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="metrics",
                description=(
                    "Deterministic metrics should match the Task 2 "
                    "data layer."
                ),
                weight=0.15,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="risk_detection",
                description=(
                    "The brief should recognize meaningful risk signals "
                    "without inventing unsupported risks."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="summary_quality",
                description=(
                    "The executive summary should accurately connect the "
                    "strongest account-level signals."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="actionability",
                description=(
                    "Talking points should focus on concrete TAM actions "
                    "and customer discussion."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
        ],
    ),

    EvaluationCase(
        case_id="T2-03",
        task="task2",
        name="Escalation-heavy account",
        description=(
            "Account with stronger support/escalation indicators."
        ),
        input_data={
            "account_id": "ACC-1881",
            "days": 90,
            "analysis_date": date(2026, 8, 27),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="account_identity",
                description=(
                    "The brief should use the correct account identity."
                ),
                weight=0.10,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="metrics",
                description=(
                    "Account metrics should match values produced by "
                    "Task 2's data layer."
                ),
                weight=0.15,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="ticket_window",
                description=(
                    "Risk findings must only reference tickets returned "
                    "for the requested analysis window."
                ),
                weight=0.15,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="risk_evidence",
                description=(
                    "Every flagged ticket risk must contain an evidence "
                    "quote from the ticket."
                ),
                weight=0.15,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="risk_quality",
                description=(
                    "The identified risks should be genuinely meaningful "
                    "rather than merely repeating every support ticket."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="summary_quality",
                description=(
                    "The executive summary should accurately synthesize "
                    "account and recent support activity."
                ),
                weight=0.10,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="actionability",
                description=(
                    "Talking points should prioritize concrete risk "
                    "discussion and next steps."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
        ],
    ),

    EvaluationCase(
        case_id="T2-04",
        task="task2",
        name="Narrow analysis window",
        description=(
            "Tests whether the summarizer respects a very small ticket "
            "history window."
        ),
        input_data={
            "account_id": "ACC-7397",
            "days": 1,
            "analysis_date": date(2026, 8, 27),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="window_correctness",
                description=(
                    "The final output must respect the selected one-day "
                    "analysis window and must not treat older tickets as "
                    "recent."
                ),
                weight=0.25,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="account_identity",
                description=(
                    "The brief should refer to the correct account."
                ),
                weight=0.10,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="required_sections",
                description=(
                    "All three required brief sections should be present."
                ),
                weight=0.15,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="no_ticket_hallucination",
                description=(
                    "The brief should not claim recent ticket activity "
                    "that is outside the selected window."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="summary_quality",
                description=(
                    "The brief should remain useful based on the available "
                    "account-level information even when the ticket window "
                    "is narrow."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="actionability",
                description=(
                    "Talking points should still be reasonable and grounded "
                    "despite limited recent ticket history."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
        ],
    ),

    EvaluationCase(
        case_id="T2-05",
        task="task2",
        name="Historical window regression",
        description=(
            "Tests whether changing the analysis date changes the selected "
            "ticket history appropriately."
        ),
        input_data={
            "account_id": "ACC-3930",
            "days": 90,
            "analysis_date": date(2026, 5, 31),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="window_correctness",
                description=(
                    "The output must be based on tickets that fall within "
                    "the requested historical 90-day window."
                ),
                weight=0.25,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="metrics",
                description=(
                    "Ticket-derived metrics should match the historical "
                    "window returned by Task 2's data layer."
                ),
                weight=0.20,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="account_identity",
                description=(
                    "The account identity must remain correct."
                ),
                weight=0.10,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="historical_grounding",
                description=(
                    "The brief should not describe events from outside "
                    "the selected historical window as recent activity."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="summary_quality",
                description=(
                    "The executive summary should accurately synthesize "
                    "the account at the selected historical point."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="actionability",
                description=(
                    "Talking points should be grounded in the selected "
                    "historical context."
                ),
                weight=0.10,
                evaluation_type="llm",
            ),
        ],
    ),

    EvaluationCase(
        case_id="T2-06",
        task="task2",
        name="Account-ticket inconsistency",
        description=(
            "Adversarial regression case using the actual dataset's mismatch "
            "between account-level and ticket-level company fields."
        ),
        input_data={
            "account_id": "ACC-7397",
            "days": 90,
            "analysis_date": date(2026, 8, 27),
        },
        criteria=[
            EvaluationCriterion(
                criterion_id="account_identity",
                description=(
                    "The account identity should match the account record "
                    "for ACC-7397."
                ),
                weight=0.15,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="ticket_window",
                description=(
                    "Only tickets returned by Task 2's selected 90-day "
                    "window may be treated as recent ticket activity."
                ),
                weight=0.20,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="risk_evidence",
                description=(
                    "Any ticket-level risk evidence must come from the "
                    "actual ticket body."
                ),
                weight=0.15,
                evaluation_type="rule",
            ),
            EvaluationCriterion(
                criterion_id="source_distinction",
                description=(
                    "The summary should distinguish account-level facts "
                    "from individual ticket-level facts, especially "
                    "account P1 counts versus individual ticket urgency."
                ),
                weight=0.20,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="historical_accuracy",
                description=(
                    "The output should not describe an April ticket as "
                    "recent relative to the August 27 analysis date."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
            EvaluationCriterion(
                criterion_id="no_contradictory_claims",
                description=(
                    "The model should not claim that an individual ticket "
                    "is P1 when that ticket's own urgency is P3."
                ),
                weight=0.15,
                evaluation_type="llm",
            ),
        ],
        adversarial=True,
    ),
]


ALL_CASES = (
    TASK1_CASES
    + TASK2_CASES
)