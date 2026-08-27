from prompts.prompt_account_analysis_human import ACCOUNT_ANALYSIS_HUMAN_PROMPT
from prompts.prompt_account_analysis_system import ACCOUNT_ANALYSIS_SYSTEM_PROMPT
from prompts.prompt_final_brief_human import FINAL_BRIEF_HUMAN_PROMPT
from prompts.prompt_final_brief_system import FINAL_BRIEF_SYSTEM_PROMPT
from prompts.prompt_risk_detection_human import RISK_DETECTION_HUMAN_PROMPT
from prompts.prompt_risk_detection_system import RISK_DETECTION_SYSTEM_PROMPT
from prompts.prompt_risk_repair_system import RISK_REPAIR_SYSTEM_PROMPT
from prompts.prompt_risk_repair_human import RISK_REPAIR_HUMAN_PROMPT


# =============================================================================
# Prompt construction helpers
# =============================================================================

def build_account_analysis_messages(
    account: str,
    metrics: str,
    tickets: str,
    days: int = 90,
) -> list[tuple[str, str]]:
    """
    Build messages for the account-analysis chain.

    This helper keeps prompt formatting out of summary.py.
    """

    human_prompt = ACCOUNT_ANALYSIS_HUMAN_PROMPT.format(
        account=account,
        metrics=metrics,
        tickets=tickets,
        days=days,
    )

    return [
        ("system", ACCOUNT_ANALYSIS_SYSTEM_PROMPT),
        ("human", human_prompt),
    ]


def build_risk_detection_messages(
    account: str,
    account_analysis: str,
    metrics: str,
    tickets: str,
) -> list[tuple[str, str]]:
    """
    Build messages for the risk-detection chain.
    """

    human_prompt = RISK_DETECTION_HUMAN_PROMPT.format(
        account=account,
        account_analysis=account_analysis,
        metrics=metrics,
        tickets=tickets,
    )

    return [
        ("system", RISK_DETECTION_SYSTEM_PROMPT),
        ("human", human_prompt),
    ]


def build_final_brief_messages(
    account: str,
    metrics: str,
    account_analysis: str,
    risk_analysis: str,
) -> list[tuple[str, str]]:
    """
    Build messages for the final TAM brief chain.
    """

    human_prompt = FINAL_BRIEF_HUMAN_PROMPT.format(
        account=account,
        metrics=metrics,
        account_analysis=account_analysis,
        risk_analysis=risk_analysis,
    )

    return [
        ("system", FINAL_BRIEF_SYSTEM_PROMPT),
        ("human", human_prompt),
    ]


def build_risk_repair_messages(
    tickets: str,
    risk_analysis: str,
    validation_errors: str,
) -> list[tuple[str, str]]:
    """
    Build messages for the risk-evidence repair chain.
    """

    human_prompt = RISK_REPAIR_HUMAN_PROMPT.format(
        tickets=tickets,
        risk_analysis=risk_analysis,
        validation_errors=validation_errors,
    )

    return [
        ("system", RISK_REPAIR_SYSTEM_PROMPT),
        ("human", human_prompt),
    ]