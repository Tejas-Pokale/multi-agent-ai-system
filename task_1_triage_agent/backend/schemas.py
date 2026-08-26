from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# INPUT ENUMS
# ============================================================

class Channel(str, Enum):
    EMAIL = "email"
    PORTAL = "portal"
    CHAT = "chat"
    PHONE = "phone"


class PlanTier(str, Enum):
    STARTER = "Starter"
    PROFESSIONAL = "Professional"
    BUSINESS = "Business"
    ENTERPRISE = "Enterprise"


# ============================================================
# CLASSIFICATION ENUMS
# ============================================================

class IssueCategory(str, Enum):
    BUG = "Bug"
    FEATURE_REQUEST = "Feature Request"
    HOW_TO = "How-To"
    PERFORMANCE = "Performance"
    BILLING = "Billing"
    INTEGRATION = "Integration"
    ONBOARDING = "Onboarding"
    DATA_LOSS = "Data Loss"


class Urgency(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class TicketStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    PENDING_CUSTOMER = "Pending Customer"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


# ============================================================
# INPUT
# ============================================================

class TicketInput(BaseModel):
    """
    Incoming support ticket.

    Only subject and body are required because the triage
    agent is responsible for determining product area,
    category and urgency.
    """

    model_config = ConfigDict(
        extra="ignore"
    )

    subject: str = Field(
        ...,
        min_length=1,
        description="Support ticket subject."
    )

    body: str = Field(
        ...,
        min_length=1,
        description="Full support ticket body."
    )

    # --------------------------------------------------------
    # Optional contextual information
    # --------------------------------------------------------

    ticket_id: Optional[str] = Field(
        default=None,
        description="Existing ticket identifier if available."
    )

    account_id: Optional[str] = Field(
        default=None,
        description="Customer account identifier if available."
    )

    company: Optional[str] = Field(
        default=None,
        description="Customer/company name."
    )

    product: Optional[str] = Field(
        default=None,
        description="Product explicitly supplied with the ticket."
    )

    channel: Optional[Channel] = Field(
        default=None,
        description="Channel through which the ticket was received."
    )

    plan_tier: Optional[PlanTier] = Field(
        default=None,
        description="Customer subscription tier."
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Optional tags supplied with the ticket."
    )


# ============================================================
# KNOWLEDGE BASE MATCH
# ============================================================

class KnowledgeBaseMatch(BaseModel):
    """
    Relevant knowledge-base document/section retrieved
    for the incoming ticket.
    """

    source: str = Field(
        ...,
        description="Knowledge-base source file."
    )

    section: Optional[str] = Field(
        default=None,
        description="Matched section title."
    )

    category: Optional[str] = Field(
        default=None,
        description="Knowledge-base category."
    )

    product: Optional[str] = Field(
        default=None,
        description="Product associated with the document."
    )

    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Similarity/relevance score."
    )

    excerpt: Optional[str] = Field(
        default=None,
        description="Relevant excerpt from the knowledge-base document."
    )


# ============================================================
# SIMILAR HISTORICAL TICKET
# ============================================================

class SimilarTicket(BaseModel):
    """
    Historical ticket retrieved from the ticket collection.
    """

    ticket_id: str = Field(
        ...,
        description="Historical ticket ID."
    )

    similarity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Semantic similarity score."
    )

    product: Optional[str] = None

    product_area: Optional[str] = None

    category: Optional[IssueCategory] = None

    urgency: Optional[Urgency] = None

    status: Optional[TicketStatus] = None


# ============================================================
# FINAL TRIAGE OUTPUT
# ============================================================

class TriageResult(BaseModel):
    """
    Final structured output produced by the triage agent.
    """

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    product_area: str = Field(
        ...,
        description=(
            "Product/module area identified from the ticket. "
            "Examples: Connectors, Authentication, Data Sources."
        )
    )

    category: IssueCategory = Field(
        ...,
        description="Issue category assigned to the ticket."
    )

    urgency: Urgency = Field(
        ...,
        description="Urgency tier from P1 to P4."
    )

    # --------------------------------------------------------
    # Reasoning
    # --------------------------------------------------------

    reasoning: str = Field(
        ...,
        min_length=1,
        description=(
            "Concise explanation supporting the "
            "classification and urgency."
        )
    )

    # --------------------------------------------------------
    # Knowledge-base matching
    # --------------------------------------------------------

    known_issue: bool = Field(
        ...,
        description=(
            "Whether the ticket matches a known issue "
            "or relevant pattern in the knowledge base."
        )
    )

    knowledge_base_match: Optional[KnowledgeBaseMatch] = Field(
        default=None,
        description="Most relevant knowledge-base match."
    )

    # --------------------------------------------------------
    # Historical ticket evidence
    # --------------------------------------------------------

    similar_tickets: list[SimilarTicket] = Field(
        default_factory=list,
        description=(
            "Relevant historical tickets used as "
            "supporting evidence."
        )
    )

    # --------------------------------------------------------
    # Routing
    # --------------------------------------------------------

    recommended_team: str = Field(
        ...,
        min_length=1,
        description=(
            "Recommended support team responsible "
            "for handling the ticket."
        )
    )

    # --------------------------------------------------------
    # Customer response
    # --------------------------------------------------------

    draft_response: str = Field(
        ...,
        min_length=1,
        description=(
            "Draft first-response message that a support "
            "agent can send to the customer."
        )
    )