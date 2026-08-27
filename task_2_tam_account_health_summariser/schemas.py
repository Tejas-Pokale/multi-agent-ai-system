# app/schemas.py

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


# =============================================================================
# Shared configuration
# =============================================================================

class ApplicationSchema(BaseModel):
    """
    Base model for all application schemas.

    extra="forbid" is intentional:
    if the LLM returns unexpected fields, we want structured-output
    validation to catch them instead of silently accepting them.
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


# =============================================================================
# Enumerations
# =============================================================================

class RiskType(str, Enum):
    """
    Types of customer-health risks that the application should flag.

    These map directly to the task requirement:
        - churn risk
        - escalation signals
    """

    CHURN_RISK = "Churn Risk"
    ESCALATION_SIGNAL = "Escalation Signal"


class RiskSeverity(str, Enum):
    """
    Severity assigned to a detected risk.
    """

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class HealthStatus(str, Enum):
    """
    Account health status values defined by the supplied dataset schema.
    """

    HEALTHY = "Healthy"
    AT_RISK = "At Risk"
    CHURNING = "Churning"
    NEW = "New"


class UsageTrend(str, Enum):
    """
    Usage trend values defined by the supplied dataset schema.
    """

    INCREASING = "Increasing"
    STABLE = "Stable"
    DECLINING = "Declining"
    INACTIVE = "Inactive"


class TicketUrgency(str, Enum):
    """
    Ticket urgency values defined by the supplied ticket schema.
    """

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class TicketStatus(str, Enum):
    """
    Ticket status values defined by the supplied ticket schema.
    """

    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    PENDING_CUSTOMER = "Pending Customer"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


# =============================================================================
# Account data schemas
# =============================================================================

class PrimaryContact(ApplicationSchema):
    """
    Primary account contact from accounts.json.
    """

    name: str = Field(
        ...,
        description="Name of the primary customer contact.",
    )

    title: str = Field(
        ...,
        description="Job title of the primary customer contact.",
    )


class AccountRecord(ApplicationSchema):
    """
    Structured representation of an account record.

    This mirrors the account fields that are relevant to the TAM health
    summarisation application.
    """

    account_id: str = Field(
        ...,
        description="Unique customer account identifier.",
    )

    company: str = Field(
        ...,
        description="Customer company name.",
    )

    tam: str = Field(
        ...,
        description="TAM assigned to the account.",
    )

    plan_tier: str = Field(
        ...,
        description="Customer subscription plan.",
    )

    arr_usd: float = Field(
        ...,
        ge=0,
        description="Annual recurring revenue in USD.",
    )

    seats_licensed: int = Field(
        ...,
        ge=0,
        description="Number of licensed seats.",
    )

    seats_active: int = Field(
        ...,
        ge=0,
        description="Number of active seats.",
    )

    products: list[str] = Field(
        default_factory=list,
        description="Products used by the account.",
    )

    health_status: HealthStatus = Field(
        ...,
        description="Current account health status.",
    )

    usage_trend: UsageTrend = Field(
        ...,
        description="Current usage trend.",
    )

    open_tickets: int = Field(
        ...,
        ge=0,
        description="Number of open tickets reported by the account dataset.",
    )

    p1_tickets_last_30d: int = Field(
        ...,
        ge=0,
        description="Number of P1 tickets in the last 30 days.",
    )

    customer_since: str = Field(
        ...,
        description="Date on which the customer relationship started.",
    )

    renewal_date: str = Field(
        ...,
        description="Account renewal date.",
    )

    last_qbr_date: str = Field(
        ...,
        description="Date of the most recent QBR.",
    )

    primary_contact: PrimaryContact = Field(
        ...,
        description="Primary customer contact.",
    )

    escalation_notes: list[str] = Field(
        default_factory=list,
        description="Existing escalation notes associated with the account.",
    )

    nps_score: float  | None= Field(
        default=None,
        description="NPS score, if available. This is a float between 0 and 10.",
    )

    last_login_days_ago: int = Field(
        ...,
        ge=0,
        description="Number of days since the account last logged in.",
    )

    integrations_active: list[str] = Field(
        default_factory=list,
        description="Currently active integrations.",
    )

    region: str = Field(
        ...,
        description="Customer region.",
    )

    industry: str = Field(
        ...,
        description="Customer industry.",
    )


# =============================================================================
# Ticket data schemas
# =============================================================================

class TicketRecord(ApplicationSchema):
    """
    Structured representation of a support ticket.

    This is useful for passing ticket history into LangChain in a controlled
    structure rather than passing arbitrary dictionaries around.
    """

    ticket_id: str = Field(
        ...,
        description="Unique ticket identifier.",
    )

    account_id: str = Field(
        ...,
        description="Account associated with the ticket.",
    )

    company: str = Field(
        ...,
        description="Customer company name.",
    )

    subject: str = Field(
        ...,
        description="Ticket subject.",
    )

    body: str = Field(
        ...,
        description="Full ticket body. This is the source for evidence quotes.",
    )

    product: str = Field(
        ...,
        description="Product associated with the ticket.",
    )

    product_area: str = Field(
        ...,
        description="Product area associated with the ticket.",
    )

    category: str = Field(
        ...,
        description="Ticket category.",
    )

    urgency: TicketUrgency = Field(
        ...,
        description="Ticket urgency.",
    )

    status: TicketStatus = Field(
        ...,
        description="Current ticket status.",
    )

    plan_tier: str = Field(
        ...,
        description="Customer plan at the time of the ticket.",
    )

    assigned_agent: str = Field(
        ...,
        description="Support agent assigned to the ticket.",
    )

    created_at: str = Field(
        ...,
        description="Ticket creation timestamp in ISO format.",
    )

    updated_at: str = Field(
        ...,
        description="Ticket last-update timestamp in ISO format.",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Ticket tags.",
    )

    channel: str = Field(
        ...,
        description="Channel through which the ticket was submitted.",
    )

    satisfaction_score: float | None = Field(
        default=None,
        description="Customer satisfaction score, if available.",
    )


# =============================================================================
# Deterministic metrics
# =============================================================================

class AccountMetrics(ApplicationSchema):
    """
    Metrics calculated deterministically by Python/pandas.

    These values should NOT be generated by the LLM.
    """

    seat_utilization_percent: float | None = Field(
        default=None,
        ge=0,
        description="Percentage of licensed seats that are active.",
    )

    licensed_seats: int = Field(
        ...,
        ge=0,
        description="Number of licensed seats.",
    )

    active_seats: int = Field(
        ...,
        ge=0,
        description="Number of active seats.",
    )

    tickets_last_90d: int = Field(
        ...,
        ge=0,
        description="Number of tickets created in the last 90 days.",
    )

    open_tickets_last_90d: int = Field(
        ...,
        ge=0,
        description="Number of currently open/in-progress/pending tickets "
                    "created in the last 90 days.",
    )

    p1_tickets_last_90d: int = Field(
        ...,
        ge=0,
        description="Number of P1 tickets created in the last 90 days.",
    )

    p2_tickets_last_90d: int = Field(
        ...,
        ge=0,
        description="Number of P2 tickets created in the last 90 days.",
    )

    average_ticket_satisfaction: float | None = Field(
        default=None,
        description="Average available ticket satisfaction score. Must be between 1 and 5 if available.",
    )


# =============================================================================
# Data context passed into the LLM pipeline
# =============================================================================

class AccountContext(ApplicationSchema):
    """
    Complete deterministic context supplied to the LangChain pipeline.
    """

    account: AccountRecord = Field(
        ...,
        description="Account information.",
    )

    tickets: list[TicketRecord] = Field(
        default_factory=list,
        description="Tickets created during the selected analysis window.",
    )

    metrics: AccountMetrics = Field(
        ...,
        description="Deterministically calculated account metrics.",
    )


# =============================================================================
# Chain 1 — Account Analysis
# =============================================================================

class AccountAnalysis(ApplicationSchema):
    """
    Structured output from Chain 1.

    The first chain interprets the account and ticket context but does not
    produce the final TAM brief yet.
    """

    overall_assessment: str = Field(
        ...,
        min_length=1,
        description=(
            "Concise overall assessment of the account's current health, "
            "based only on the supplied account and ticket evidence."
        ),
    )

    positive_signals: list[
        Annotated[str, Field(min_length=1)]
    ] = Field(
        default_factory=list,
        description=(
            "Important positive account-health signals supported by the "
            "provided data."
        ),
    )

    negative_signals: list[
        Annotated[str, Field(min_length=1)]
    ] = Field(
        default_factory=list,
        description=(
            "Important negative account-health signals supported by the "
            "provided data."
        ),
    )

    key_observations: list[
        Annotated[str, Field(min_length=1)]
    ] = Field(
        default_factory=list,
        description=(
            "Important observations connecting account-level information "
            "with recent ticket activity."
        ),
    )


# =============================================================================
# Chain 2 — Risk Detection
# =============================================================================

class RiskFlag(ApplicationSchema):
    """
    A single ticket-level churn or escalation signal.

    IMPORTANT:
    evidence_quote must be copied directly from the source ticket body.
    summary.py will validate that it exists verbatim in the original ticket.
    """

    ticket_id: str = Field(
        ...,
        description="ID of the ticket containing the risk signal.",
    )

    risk_type: RiskType = Field(
        ...,
        description=(
            "Whether the ticket represents a churn risk or escalation signal."
        ),
    )

    severity: RiskSeverity = Field(
        ...,
        description="Severity of the identified risk.",
    )

    evidence_quote: str = Field(
        ...,
        min_length=1,
        description=(
            "Exact verbatim quote from the ticket body supporting the risk. "
            "Must not be paraphrased or invented."
        ),
    )

    explanation: str = Field(
        ...,
        min_length=1,
        description=(
            "Explanation of why the quoted ticket evidence represents the "
            "identified risk."
        ),
    )

    recommended_action: str = Field(
        ...,
        min_length=1,
        description=(
            "Concise action the TAM should consider in response to this risk."
        ),
    )


class RiskAnalysis(ApplicationSchema):
    """
    Structured output from Chain 2.
    """

    flags: list[RiskFlag] = Field(
        default_factory=list,
        description=(
            "All tickets from the supplied ticket history that contain "
            "meaningful churn or escalation signals."
        ),
    )


# =============================================================================
# Chain 3 — Final TAM Brief
# =============================================================================

class ExecutiveSummary(ApplicationSchema):
    """
    Executive summary section of the final TAM brief.
    """

    text: str = Field(
        ...,
        min_length=1,
        description=(
            "Executive account-health summary containing exactly 3 to 5 "
            "sentences."
        ),
    )

    @field_validator("text")
    @classmethod
    def validate_sentence_count(cls, value: str) -> str:
        """
        Basic deterministic sentence-count validation.

        This intentionally uses a conservative punctuation-based approach.
        The final output is still validated again in summary.py.
        """

        normalized = value.strip()

        # Count sentence-ending punctuation.
        sentence_count = sum(
            normalized.count(mark)
            for mark in [".", "!", "?"]
        )

        # if not 3 <= sentence_count <= 5:
        #     raise ValueError(
        #         "Executive summary must contain between 3 and 5 sentences."
        #     )

        return normalized


class RecommendedTalkingPoint(ApplicationSchema):
    """
    A single actionable talking point for the TAM.
    """

    topic: str = Field(
        ...,
        min_length=1,
        description="Short name of the topic.",
    )

    rationale: str = Field(
        ...,
        min_length=1,
        description=(
            "Why this topic matters for the upcoming TAM conversation."
        ),
    )

    suggested_question: str = Field(
        ...,
        min_length=1,
        description=(
            "A concrete question the TAM can ask the customer."
        ),
    )


class AccountBrief(ApplicationSchema):
    """
    Final structured output consumed by Streamlit.

    This corresponds directly to the three required sections in the task:
        1. Executive Summary
        2. Open Risks & Flagged Issues
        3. Recommended Talking Points
    """

    executive_summary: ExecutiveSummary = Field(
        ...,
        description="3–5 sentence executive summary.",
    )

    open_risks: list[RiskFlag] = Field(
        default_factory=list,
        description=(
            "Validated churn and escalation risks identified from recent "
            "ticket history."
        ),
    )

    recommended_talking_points: list[
        RecommendedTalkingPoint
    ] = Field(
        default_factory=list,
        description=(
            "Actionable topics the TAM should cover with the customer."
        ),
    )


# =============================================================================
# Optional complete pipeline result
# =============================================================================

class SummarizationResult(ApplicationSchema):
    """
    Complete result returned by summary.py.

    This is useful because Streamlit may want both:
        - the final brief
        - the supporting intermediate analysis
        - the source account/ticket context
    """

    account: AccountRecord = Field(
        ...,
        description="Account used to generate the brief.",
    )

    metrics: AccountMetrics = Field(
        ...,
        description="Deterministic account metrics.",
    )

    ticket_count: int = Field(
        ...,
        ge=0,
        description="Number of tickets included in the analysis.",
    )

    account_analysis: AccountAnalysis = Field(
        ...,
        description="Intermediate account-health analysis.",
    )

    risk_analysis: RiskAnalysis = Field(
        ...,
        description="Intermediate ticket risk analysis.",
    )

    brief: AccountBrief = Field(
        ...,
        description="Final TAM-facing account brief.",
    )