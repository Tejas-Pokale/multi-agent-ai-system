from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Generator

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from utils.get_data import get_account_context

from task_2_tam_account_health_summariser.prompts.prompt_account_analysis_human import ACCOUNT_ANALYSIS_HUMAN_PROMPT
from task_2_tam_account_health_summariser.prompts.prompt_account_analysis_system import ACCOUNT_ANALYSIS_SYSTEM_PROMPT
from task_2_tam_account_health_summariser.prompts.prompt_final_brief_human import FINAL_BRIEF_HUMAN_PROMPT
from task_2_tam_account_health_summariser.prompts.prompt_final_brief_system import FINAL_BRIEF_SYSTEM_PROMPT
from task_2_tam_account_health_summariser.prompts.prompt_risk_detection_human import RISK_DETECTION_HUMAN_PROMPT
from task_2_tam_account_health_summariser.prompts.prompt_risk_detection_system import RISK_DETECTION_SYSTEM_PROMPT
from task_2_tam_account_health_summariser.prompts.prompt_risk_repair_system import RISK_REPAIR_SYSTEM_PROMPT
from task_2_tam_account_health_summariser.prompts.prompt_risk_repair_human import RISK_REPAIR_HUMAN_PROMPT

from .schemas import (
    AccountAnalysis,
    AccountBrief,
    AccountContext,
    RiskAnalysis,
    SummarizationResult,
)


# =============================================================================
# Environment
# =============================================================================

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_LLM_MODEL = os.getenv("OPENAI_LLM_MODEL")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL")


if not OPENAI_API_KEY:
    raise EnvironmentError(
        "OPENAI_API_KEY is missing from the environment."
    )

if not OPENAI_LLM_MODEL:
    raise EnvironmentError(
        "OPENAI_LLM_MODEL is missing from the environment."
    )


# =============================================================================
# Streaming event
# =============================================================================

@dataclass
class SummaryEvent:
    """
    Event emitted during the summarisation pipeline.

    event_type:
        started
        progress
        result
        error

    message:
        Human-readable progress message.

    data:
        Optional structured data.
    """

    event_type: str
    message: str
    data: Any = None


# =============================================================================
# Account Health Summarizer
# =============================================================================

class AccountHealthSummarizer:
    """
    Main orchestration layer for the TAM Account Health Summariser.

    Pipeline:

        Account ID
            ↓
        AccountContext
            ↓
        Chain 1: Account Analysis
            ↓
        Chain 2: Risk Detection
            ↓
        Chain 3: Final TAM Brief
            ↓
        SummarizationResult

    Data retrieval and filtering are handled by get_data.py.

    Output structure is handled by schemas.py.

    Prompt definitions are handled by prompts.py.
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float = 0.0,
    ) -> None:

        self.model_name = (
            model_name or OPENAI_LLM_MODEL
        )

        self.temperature = temperature

        # ---------------------------------------------------------------------
        # LLM
        # ---------------------------------------------------------------------

        self.llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=self.model_name,
            temperature=self.temperature,
        )

        # ---------------------------------------------------------------------
        # Structured LLM outputs
        # ---------------------------------------------------------------------

        self.account_analysis_llm = (
            self.llm.with_structured_output(
                AccountAnalysis
            )
        )

        self.risk_analysis_llm = (
            self.llm.with_structured_output(
                RiskAnalysis
            )
        )

        self.account_brief_llm = (
            self.llm.with_structured_output(
                AccountBrief
            )
        )

        # ---------------------------------------------------------------------
        # Prompts
        # ---------------------------------------------------------------------

        self.account_analysis_prompt = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        ACCOUNT_ANALYSIS_SYSTEM_PROMPT,
                    ),
                    (
                        "human",
                        ACCOUNT_ANALYSIS_HUMAN_PROMPT,
                    ),
                ]
            )
        )

        self.risk_detection_prompt = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        RISK_DETECTION_SYSTEM_PROMPT,
                    ),
                    (
                        "human",
                        RISK_DETECTION_HUMAN_PROMPT,
                    ),
                ]
            )
        )

        self.final_brief_prompt = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        FINAL_BRIEF_SYSTEM_PROMPT,
                    ),
                    (
                        "human",
                        FINAL_BRIEF_HUMAN_PROMPT,
                    ),
                ]
            )
        )

        # ---------------------------------------------------------------------
        # LangChain chains
        # ---------------------------------------------------------------------

        self.account_analysis_chain = (
            self.account_analysis_prompt
            | self.account_analysis_llm
        )

        self.risk_detection_chain = (
            self.risk_detection_prompt
            | self.risk_analysis_llm
        )

        self.final_brief_chain = (
            self.final_brief_prompt
            | self.account_brief_llm
        )

    # =========================================================================
    # Public synchronous API
    # =========================================================================

    def summarize(
        self,
        account_id: str,
        days: int = 90,
        analysis_date: date | None = None,
    ) -> SummarizationResult:
        """
        Generate a complete account brief.

        This is the synchronous version of the pipeline.
        """

        context = self._load_context(
            account_id=account_id,
            days=days,
            analysis_date=analysis_date,
        )

        account_analysis = self._analyze_account(
            context=context,
            days=days,
        )

        risk_analysis = self._detect_risks(
            context=context,
            account_analysis=account_analysis,
        )

        brief = self._generate_final_brief(
            context=context,
            account_analysis=account_analysis,
            risk_analysis=risk_analysis,
        )

        return self._build_result(
            context=context,
            account_analysis=account_analysis,
            risk_analysis=risk_analysis,
            brief=brief,
        )

    # =========================================================================
    # Public streaming API
    # =========================================================================

    def summarize_stream(
        self,
        account_id: str,
        days: int = 90,
        analysis_date: date | None = None,
    ) -> Generator[SummaryEvent, None, None]:
        """
        Generate an account brief while emitting progress events.

        Streamlit can consume this generator to keep the interface responsive
        while the LLM calls are running.
        """

        yield SummaryEvent(
            event_type="started",
            message="Starting account health analysis...",
        )

        try:

            # -----------------------------------------------------------------
            # Load data
            # -----------------------------------------------------------------

            yield SummaryEvent(
                event_type="progress",
                message=(
                    f"Loading account and last {days} days "
                    "of ticket history..."
                ),
            )

            context = self._load_context(
                account_id=account_id,
                days=days,
                analysis_date=analysis_date,
            )

            ticket_count = len(
                context.tickets
            )

            yield SummaryEvent(
                event_type="progress",
                message=(
                    f"Account loaded successfully. "
                    f"{ticket_count} ticket(s) found."
                ),
                data={
                    "account_id": (
                        context.account.account_id
                    ),
                    "company": (
                        context.account.company
                    ),
                    "ticket_count": ticket_count,
                },
            )

            # -----------------------------------------------------------------
            # Chain 1
            # -----------------------------------------------------------------

            yield SummaryEvent(
                event_type="progress",
                message=(
                    "Analyzing account health and "
                    "support history..."
                ),
            )

            account_analysis = (
                self._analyze_account(
                    context=context,
                    days=days,
                )
            )

            yield SummaryEvent(
                event_type="progress",
                message="Account health analysis completed.",
                data=account_analysis,
            )

            # -----------------------------------------------------------------
            # Chain 2
            # -----------------------------------------------------------------

            yield SummaryEvent(
                event_type="progress",
                message=(
                    "Scanning tickets for churn and "
                    "escalation signals..."
                ),
            )

            risk_analysis = self._detect_risks(
                context=context,
                account_analysis=account_analysis,
            )

            yield SummaryEvent(
                event_type="progress",
                message=(
                    f"Risk detection completed. "
                    f"{len(risk_analysis.flags)} "
                    "risk signal(s) identified."
                ),
                data=risk_analysis,
            )

            # -----------------------------------------------------------------
            # Chain 3
            # -----------------------------------------------------------------

            yield SummaryEvent(
                event_type="progress",
                message=(
                    "Generating the final TAM account brief..."
                ),
            )

            brief = self._generate_final_brief(
                context=context,
                account_analysis=account_analysis,
                risk_analysis=risk_analysis,
            )

            # -----------------------------------------------------------------
            # Final result
            # -----------------------------------------------------------------

            result = self._build_result(
                context=context,
                account_analysis=account_analysis,
                risk_analysis=risk_analysis,
                brief=brief,
            )

            yield SummaryEvent(
                event_type="result",
                message="Account brief is ready.",
                data=result,
            )

        except Exception as exc:

            yield SummaryEvent(
                event_type="error",
                message=self._format_error(exc),
                data=exc,
            )

    # =========================================================================
    # Data layer
    # =========================================================================

    def _load_context(
        self,
        account_id: str,
        days: int,
        analysis_date: date | None = None,
    ) -> AccountContext:
        """
        Load account context from get_data.py and convert it into the
        AccountContext Pydantic model.

        Pydantic performs the schema validation here.
        """

        if days <= 0:
            raise ValueError(
                "days must be a positive integer."
            )

        raw_context = get_account_context(
            account_id=account_id,
            days=days,
            reference_date=analysis_date,
        )

        # Pydantic is responsible for validating the structure.
        return AccountContext(
            **raw_context
        )

    # =========================================================================
    # Chain 1 — Account analysis
    # =========================================================================

    def _analyze_account(
        self,
        context: AccountContext,
        days: int = 90,
    ) -> AccountAnalysis:
        """
        Run the first LangChain stage.
        """

        account = self._serialize(
            context.account.model_dump(
                mode="json"
            )
        )

        metrics = self._serialize(
            context.metrics.model_dump(
                mode="json"
            )
        )

        tickets = self._serialize(
            [
                ticket.model_dump(
                    mode="json"
                )
                for ticket in context.tickets
            ]
        )

        result = self.account_analysis_chain.invoke(
            {
                "account": account,
                "metrics": metrics,
                "tickets": tickets,
                "days": days,
            }
        )

        return result

    # =========================================================================
    # Chain 2 — Risk detection
    # =========================================================================

    def _detect_risks(
        self,
        context: AccountContext,
        account_analysis: AccountAnalysis,
    ) -> RiskAnalysis:
        """
        Run the second LangChain stage.
        """

        account = self._serialize(
            context.account.model_dump(
                mode="json"
            )
        )

        metrics = self._serialize(
            context.metrics.model_dump(
                mode="json"
            )
        )

        tickets = self._serialize(
            [
                ticket.model_dump(
                    mode="json"
                )
                for ticket in context.tickets
            ]
        )

        analysis = self._serialize(
            account_analysis.model_dump(
                mode="json"
            )
        )

        result = self.risk_detection_chain.invoke(
            {
                "account": account,
                "account_analysis": analysis,
                "metrics": metrics,
                "tickets": tickets,
            }
        )

        return result

    # =========================================================================
    # Chain 3 — Final TAM brief
    # =========================================================================

    def _generate_final_brief(
        self,
        context: AccountContext,
        account_analysis: AccountAnalysis,
        risk_analysis: RiskAnalysis,
    ) -> AccountBrief:
        """
        Run the final synthesis LangChain stage.
        """

        account = self._serialize(
            context.account.model_dump(
                mode="json"
            )
        )

        metrics = self._serialize(
            context.metrics.model_dump(
                mode="json"
            )
        )

        analysis = self._serialize(
            account_analysis.model_dump(
                mode="json"
            )
        )

        risks = self._serialize(
            risk_analysis.model_dump(
                mode="json"
            )
        )

        result = self.final_brief_chain.invoke(
            {
                "account": account,
                "metrics": metrics,
                "account_analysis": analysis,
                "risk_analysis": risks,
            }
        )

        return result

    # =========================================================================
    # Final result
    # =========================================================================

    @staticmethod
    def _build_result(
        context: AccountContext,
        account_analysis: AccountAnalysis,
        risk_analysis: RiskAnalysis,
        brief: AccountBrief,
    ) -> SummarizationResult:
        """
        Construct the final result consumed by Streamlit.
        """

        return SummarizationResult(
            account=context.account,
            metrics=context.metrics,
            ticket_count=len(context.tickets),
            account_analysis=account_analysis,
            risk_analysis=risk_analysis,
            brief=brief,
        )

    # =========================================================================
    # Serialization
    # =========================================================================

    @staticmethod
    def _serialize(
        value: Any,
    ) -> str:
        """
        Convert structured Python data into deterministic JSON.

        mode="json" is used before this method so enums and other Pydantic
        values are already JSON-compatible.
        """

        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )

    # =========================================================================
    # Error handling
    # =========================================================================

    @staticmethod
    def _format_error(
        exc: Exception,
    ) -> str:
        """
        Convert an exception into a useful application message.
        """

        if isinstance(exc, KeyError):
            return str(exc)

        if isinstance(exc, FileNotFoundError):
            return str(exc)

        if isinstance(exc, ValueError):
            return str(exc)

        if isinstance(exc, EnvironmentError):
            return str(exc)

        return (
            "The account health analysis could not be completed. "
            f"Technical detail: {exc}"
        )


# =============================================================================
# Shared summarizer instance
# =============================================================================

summarizer = AccountHealthSummarizer()


# =============================================================================
# Convenience API
# =============================================================================

def summarize_account(
    account_id: str,
    days: int = 90,
    analysis_date: date | None = None,
) -> SummarizationResult:
    """
    Non-streaming convenience function.
    """

    return summarizer.summarize(
        account_id=account_id,
        days=days,
        analysis_date=analysis_date,
    )


def summarize_account_stream(
    account_id: str,
    days: int = 90,
    analysis_date: date | None = None,
) -> Generator[SummaryEvent, None, None]:
    """
    Streaming convenience function for Streamlit.
    """

    yield from summarizer.summarize_stream(
        account_id=account_id,
        days=days,
        analysis_date=analysis_date,
    )


# =============================================================================
# Local test
# =============================================================================

if __name__ == "__main__":

    DEMO_ACCOUNT_ID = "ACC-3336"

    print(
        f"\nGenerating account brief for "
        f"{DEMO_ACCOUNT_ID}...\n"
    )

    for event in summarize_account_stream(
        account_id=DEMO_ACCOUNT_ID,
        days=90,
    ):

        if event.event_type == "started":

            print(
                f"[START] {event.message}"
            )

        elif event.event_type == "progress":

            print(
                f"[INFO]  {event.message}"
            )

        elif event.event_type == "result":

            result: SummarizationResult = (
                event.data
            )

            print(
                "\n[DONE] Account brief generated.\n"
            )

            print(
                "=" * 70
            )

            print(
                "EXECUTIVE SUMMARY"
            )

            print(
                "=" * 70
            )

            print(
                result.brief
                .executive_summary
                .text
            )

            print(
                "\n"
                + "=" * 70
            )

            print(
                "OPEN RISKS"
            )

            print(
                "=" * 70
            )

            if not result.brief.open_risks:

                print(
                    "No meaningful churn or "
                    "escalation signals identified."
                )

            else:

                for risk in (
                    result.brief.open_risks
                ):

                    print(
                        f"\n[{risk.severity.value}] "
                        f"{risk.risk_type.value}"
                    )

                    print(
                        f"Ticket: {risk.ticket_id}"
                    )

                    print(
                        f"Evidence: "
                        f"{risk.evidence_quote}"
                    )

                    print(
                        f"Explanation: "
                        f"{risk.explanation}"
                    )

                    print(
                        f"Action: "
                        f"{risk.recommended_action}"
                    )

            print(
                "\n"
                + "=" * 70
            )

            print(
                "TALKING POINTS"
            )

            print(
                "=" * 70
            )

            for index, point in enumerate(
                result.brief
                .recommended_talking_points,
                start=1,
            ):

                print(
                    f"\n{index}. "
                    f"{point.topic}"
                )

                print(
                    f"Why: "
                    f"{point.rationale}"
                )

                print(
                    f"Ask: "
                    f"{point.suggested_question}"
                )

        elif event.event_type == "error":

            print(
                f"[ERROR] {event.message}"
            )