# app/app.py

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from task_2_tam_account_health_summariser.summary import (
    SummaryEvent,
    summarize_account_stream,
)


# =============================================================================
# Page configuration
# =============================================================================

st.set_page_config(
    page_title="TAM Account Health",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# HTML rendering helper
#
# IMPORTANT: st.markdown runs content through a standard Markdown parser.
# Markdown treats any line indented by 4+ spaces as a *preformatted code
# block*. Because HTML snippets below are written as indented Python
# triple-quoted strings (to stay readable in source), every line inherits
# that indentation — which caused raw "<div class=...>" tags to render as
# literal text instead of being interpreted as HTML.
#
# render_html() strips leading whitespace from every line before handing
# it to st.markdown, so nested/indented HTML always renders correctly.
# =============================================================================

def render_html(content: str) -> None:
    lines = [line.strip() for line in content.strip("\n").splitlines()]
    st.markdown("\n".join(lines), unsafe_allow_html=True)


# =============================================================================
# Custom CSS — full dark mode
# =============================================================================

render_html(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

    <style>

    /* ================================================================
       Design tokens
       ================================================================ */

    :root {
        --bg:            #090b10;
        --bg-elevated:    #10131b;
        --surface:        #141822;
        --surface-2:      #1a1f2c;
        --border:         #262c3b;
        --border-soft:    #1e2330;
        --text-primary:   #edeef3;
        --text-secondary: #a3aabd;
        --text-muted:     #6c7488;
        --accent:         #7c9dff;
        --accent-2:       #b17cff;
        --accent-soft:    rgba(124, 157, 255, 0.14);
        --accent-strong:  #a9bdff;
        --success:        #3ddc9a;
        --success-bg:     rgba(61, 220, 154, 0.10);
        --success-border: rgba(61, 220, 154, 0.28);
        --danger:         #ff6b6b;
        --danger-bg:      rgba(255, 107, 107, 0.12);
        --danger-border:  rgba(255, 107, 107, 0.30);
        --warning:        #ffc24b;
        --warning-bg:     rgba(255, 194, 75, 0.12);
        --warning-border: rgba(255, 194, 75, 0.30);
        --info:           #5fb4ff;
        --info-bg:        rgba(95, 180, 255, 0.10);
        --info-border:    rgba(95, 180, 255, 0.26);
        --shadow-glow:    0 8px 28px rgba(0, 0, 0, 0.45);
    }

    /* ================================================================
       Global
       ================================================================ */

    html, body, .stApp {
        background: var(--bg) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .stApp {
        background:
            radial-gradient(ellipse 900px 500px at 10% -5%, rgba(124,157,255,0.10) 0%, transparent 55%),
            radial-gradient(ellipse 700px 500px at 95% 0%, rgba(177,124,255,0.07) 0%, transparent 50%),
            var(--bg) !important;
        background-attachment: fixed !important;
    }

    .block-container {
        max-width: 1360px;
        padding-top: 1.5rem;
        padding-bottom: 4rem;
    }

    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: #2a3142; border-radius: 8px; }
    ::-webkit-scrollbar-thumb:hover { background: #384159; }

    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: var(--text-primary);
    }

    a { color: var(--accent); }

    hr, [data-testid="stDivider"] {
        border-color: var(--border) !important;
        margin: 1.6rem 0 !important;
    }

    code {
        background: var(--surface-2) !important;
        color: var(--accent-strong) !important;
        font-family: 'JetBrains Mono', monospace !important;
        border: 1px solid var(--border-soft) !important;
    }


    /* ================================================================
       Header
       ================================================================ */

    .hero {
        padding: 2.3rem 2.4rem;
        border-radius: 20px;
        margin-bottom: 1.7rem;
        background: linear-gradient(150deg, #12162350 0%, #171d2e90 55%, #1b223690 100%);
        border: 1px solid var(--border);
        box-shadow: var(--shadow-glow);
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(6px);
    }

    .hero::before {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 20px;
        padding: 1px;
        background: linear-gradient(120deg, rgba(124,157,255,0.5), rgba(177,124,255,0.15), transparent 60%);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }

    .hero::after {
        content: "";
        position: absolute;
        top: -50%;
        right: -8%;
        width: 360px;
        height: 360px;
        background: radial-gradient(circle, rgba(124,157,255,0.18) 0%, transparent 70%);
        pointer-events: none;
    }

    .hero-eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        color: var(--accent-strong);
        font-size: 0.74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.7rem;
        background: var(--accent-soft);
        padding: 0.3rem 0.7rem;
        border-radius: 999px;
        border: 1px solid rgba(124,157,255,0.25);
    }

    .hero-title {
        color: #f7f8fc;
        font-size: 2.3rem;
        font-weight: 800;
        letter-spacing: -0.035em;
        margin: 0;
        background: linear-gradient(90deg, #ffffff 0%, #cdd6f5 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        color: var(--text-secondary);
        font-size: 1.01rem;
        margin-top: 0.6rem;
        margin-bottom: 0;
        max-width: 620px;
        line-height: 1.55;
    }


    /* ================================================================
       Section headers
       ================================================================ */

    .section-title {
        font-size: 1.3rem;
        font-weight: 750;
        color: var(--text-primary);
        margin-top: 2.1rem;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.55rem;
        letter-spacing: -0.01em;
    }

    .section-description {
        color: var(--text-secondary);
        font-size: 0.9rem;
        margin-bottom: 1.15rem;
    }


    /* ================================================================
       Account overview cards
       ================================================================ */

    .metric-card {
        background: linear-gradient(160deg, var(--surface) 0%, var(--bg-elevated) 100%);
        border: 1px solid var(--border-soft);
        border-radius: 14px;
        padding: 1.05rem 1.2rem;
        min-height: 105px;
        transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
    }

    .metric-card:hover {
        border-color: rgba(124,157,255,0.35);
        transform: translateY(-2px);
        box-shadow: 0 10px 24px rgba(0,0,0,0.35);
    }

    .metric-label {
        color: var(--text-muted);
        font-size: 0.73rem;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .metric-value {
        color: var(--text-primary);
        font-size: 1.34rem;
        font-weight: 750;
        margin-top: 0.35rem;
        letter-spacing: -0.015em;
    }

    .metric-subtitle {
        color: var(--text-muted);
        font-size: 0.78rem;
        margin-top: 0.28rem;
    }


    /* ================================================================
       Risk cards
       ================================================================ */

    .risk-card {
        background: linear-gradient(160deg, var(--surface) 0%, var(--bg-elevated) 100%);
        border: 1px solid var(--border-soft);
        border-left: 3px solid var(--border);
        border-radius: 14px;
        padding: 1.3rem 1.4rem;
        margin-bottom: 1.05rem;
        box-shadow: var(--shadow-glow);
    }

    .risk-card.sev-high   { border-left-color: var(--danger); }
    .risk-card.sev-medium { border-left-color: var(--warning); }
    .risk-card.sev-low    { border-left-color: var(--info); }

    .risk-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 0.5rem;
        gap: 0.75rem;
    }

    .risk-type {
        font-size: 1.02rem;
        font-weight: 720;
        color: var(--text-primary);
    }

    .risk-ticket {
        color: var(--text-muted);
        font-size: 0.8rem;
        margin-top: 0.22rem;
        font-family: 'JetBrains Mono', monospace;
    }

    .risk-label {
        font-size: 0.72rem;
        font-weight: 720;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--text-muted);
        margin-top: 1rem;
        margin-bottom: 0.4rem;
    }

    .risk-body {
        color: var(--text-secondary);
        font-size: 0.92rem;
        line-height: 1.58;
    }

    .risk-quote {
        background: var(--bg-elevated);
        border: 1px solid var(--border-soft);
        border-left: 3px solid var(--text-muted);
        border-radius: 9px;
        padding: 0.9rem 1.05rem;
        color: var(--text-secondary);
        font-size: 0.9rem;
        font-style: italic;
        line-height: 1.58;
    }

    .severity-badge {
        padding: 0.3rem 0.72rem;
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 750;
        letter-spacing: 0.04em;
        white-space: nowrap;
    }

    .severity-high {
        background: var(--danger-bg);
        color: var(--danger);
        border: 1px solid var(--danger-border);
    }

    .severity-medium {
        background: var(--warning-bg);
        color: var(--warning);
        border: 1px solid var(--warning-border);
    }

    .severity-low {
        background: var(--info-bg);
        color: var(--info);
        border: 1px solid var(--info-border);
    }


    /* ================================================================
       Talking point cards
       ================================================================ */

    .talking-point {
        background: linear-gradient(160deg, var(--surface) 0%, var(--bg-elevated) 100%);
        border: 1px solid var(--border-soft);
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.9rem;
        display: flex;
        gap: 0.95rem;
        box-shadow: var(--shadow-glow);
        transition: border-color 0.18s ease;
    }

    .talking-point:hover {
        border-color: rgba(124,157,255,0.3);
    }

    .talking-point-index {
        flex-shrink: 0;
        width: 28px;
        height: 28px;
        border-radius: 9px;
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 100%);
        color: #0b0e14;
        font-size: 0.84rem;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 0.05rem;
    }

    .talking-point-title {
        color: var(--text-primary);
        font-weight: 720;
        font-size: 1rem;
    }

    .talking-point-rationale {
        color: var(--text-secondary);
        font-size: 0.89rem;
        line-height: 1.58;
        margin-top: 0.4rem;
    }

    .talking-point-question {
        color: var(--accent-strong);
        font-size: 0.88rem;
        font-weight: 600;
        margin-top: 0.65rem;
        padding-top: 0.65rem;
        border-top: 1px dashed var(--border);
    }


    /* ================================================================
       Empty / success / info states
       ================================================================ */

    .success-box {
        background: var(--success-bg);
        border: 1px solid var(--success-border);
        border-radius: 12px;
        padding: 1.05rem 1.15rem;
        color: var(--success);
        font-weight: 650;
        font-size: 0.92rem;
    }

    .empty-box {
        background: var(--bg-elevated);
        border: 1px dashed var(--border);
        border-radius: 14px;
        padding: 1.7rem;
        text-align: center;
        color: var(--text-muted);
    }

    .exec-summary-box {
        background: linear-gradient(160deg, var(--surface) 0%, var(--bg-elevated) 100%);
        border: 1px solid var(--border-soft);
        border-left: 3px solid var(--accent);
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        color: var(--text-primary);
        font-size: 0.98rem;
        line-height: 1.7;
        box-shadow: var(--shadow-glow);
    }


    /* ================================================================
       Streamlit native components — dark mode + contrast fixes
       ================================================================ */

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-elevated) 0%, var(--bg) 100%) !important;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] * {
        color: var(--text-primary);
    }

    [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {
        color: var(--text-muted) !important;
    }

    /* Widget labels (Account ID, Analysis date, etc.) */
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p,
    .stTextInput label, .stNumberInput label, .stDateInput label,
    .stSelectbox label, .stTextArea label {
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
        font-size: 0.86rem !important;
    }

    /* Text / number / date inputs — force readable text on dark surface */
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTextArea textarea,
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {
        background: var(--surface-2) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 9px !important;
        caret-color: var(--accent) !important;
    }

    .stTextInput input::placeholder,
    .stNumberInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: var(--text-muted) !important;
        opacity: 1 !important;
    }

    div[data-baseweb="input"],
    div[data-baseweb="textarea"],
    div[data-baseweb="select"] > div {
        background: var(--surface-2) !important;
        border-color: var(--border) !important;
    }

    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stDateInput input:focus,
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"] > div:focus-within {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 1px var(--accent) !important;
    }

    /* Number input +/- buttons */
    .stNumberInput button {
        background: var(--surface-2) !important;
        border-color: var(--border) !important;
        color: var(--text-primary) !important;
    }

    /* Date picker calendar popover */
    div[data-baseweb="calendar"], div[data-baseweb="popover"] {
        background: var(--surface) !important;
        color: var(--text-primary) !important;
    }

    div[data-baseweb="calendar"] * {
        color: var(--text-primary) !important;
    }

    /* Selectbox dropdown menu items */
    ul[data-testid="stSelectboxVirtualDropdown"] li,
    div[role="listbox"] {
        background: var(--surface) !important;
        color: var(--text-primary) !important;
    }

    /* Buttons */
    .stButton button, [data-testid="stBaseButton-secondary"] {
        border-radius: 10px !important;
        font-weight: 650 !important;
        border: 1px solid var(--border) !important;
        transition: all 0.15s ease !important;
    }

    .stButton button[kind="primary"], [data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #6f8dff 0%, #9c7cff 100%) !important;
        color: #0a0c12 !important;
        border: none !important;
        box-shadow: 0 8px 22px rgba(124, 109, 255, 0.32);
        font-weight: 750 !important;
    }

    .stButton button[kind="primary"]:hover {
        filter: brightness(1.1);
        box-shadow: 0 10px 26px rgba(124, 109, 255, 0.44);
        transform: translateY(-1px);
    }

    /* Alert boxes (st.info / st.error / st.success / st.warning) */
    [data-testid="stAlert"] {
        background: var(--info-bg) !important;
        border: 1px solid var(--info-border) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
    }

    [data-testid="stAlert"] p { color: var(--text-primary) !important; }

    div[data-baseweb="notification"] { color: var(--text-primary) !important; }

    /* Captions */
    .stCaption, small, [data-testid="stCaptionContainer"] {
        color: var(--text-muted) !important;
    }

    /* Markdown body default */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li {
        color: var(--text-primary);
    }

    [data-testid="stMarkdownContainer"] h3 {
        color: var(--text-primary);
        font-weight: 750;
    }


    /* ================================================================
       Streaming / generation status panel
       ================================================================ */

    [data-testid="stStatusWidget"], [data-testid="stExpander"] details {
        background: linear-gradient(160deg, var(--surface) 0%, var(--bg-elevated) 100%) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 14px !important;
        box-shadow: var(--shadow-glow);
    }

    [data-testid="stStatusWidget"] summary, [data-testid="stExpander"] summary {
        color: var(--text-primary) !important;
        font-weight: 650;
    }

    .stream-log {
        display: flex;
        flex-direction: column;
        gap: 0;
        padding: 0.3rem 0.1rem 0.1rem 0.1rem;
    }

    .stream-row {
        display: flex;
        align-items: flex-start;
        gap: 0.85rem;
        padding: 0.65rem 0.2rem;
        font-size: 0.87rem;
        color: var(--text-secondary);
        animation: fadeIn 0.3s ease;
        position: relative;
    }

    .stream-row::before {
        content: "";
        position: absolute;
        left: 15px;
        top: 34px;
        bottom: -4px;
        width: 1px;
        background: var(--border);
    }

    .stream-row:last-child::before {
        display: none;
    }

    .stream-row.stream-start {
        color: var(--text-primary);
        font-weight: 650;
    }

    .stream-icon {
        flex-shrink: 0;
        width: 30px;
        height: 30px;
        border-radius: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
        background: var(--accent-soft);
        color: var(--accent-strong);
        border: 1px solid var(--border-soft);
        z-index: 1;
    }

    .stream-text {
        padding-top: 0.28rem;
    }

    .stream-row.stream-start .stream-icon {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 100%);
        color: #0a0c12;
        border: none;
    }

    .stream-row.stream-success .stream-icon {
        background: var(--success-bg);
        color: var(--success);
        border-color: var(--success-border);
    }

    .stream-row.stream-success .stream-text {
        color: var(--success);
        font-weight: 650;
    }

    .stream-row.stream-error .stream-icon {
        background: var(--danger-bg);
        color: var(--danger);
        border-color: var(--danger-border);
    }

    .stream-row.stream-error .stream-text {
        color: var(--danger);
        font-weight: 650;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-4px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    </style>
    """
)


# =============================================================================
# Helper functions
# =============================================================================

def render_metric(
    label: str,
    value: str,
    subtitle: str = "",
) -> None:
    """
    Render a compact account metric card.
    """

    render_html(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtitle">{subtitle}</div>
        </div>
        """
    )


def format_currency(value: float | int | None) -> str:
    """
    Format USD values for display.
    """

    if value is None:
        return "—"

    value = float(value)

    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"

    if value >= 1_000:
        return f"${value / 1_000:.0f}K"

    return f"${value:,.0f}"


def format_health_status(status: str) -> str:
    """
    Add a simple visual indicator to account health.
    """

    indicators = {
        "Healthy": "🟢",
        "At Risk": "🟠",
        "Churning": "🔴",
        "New": "🔵",
    }

    return f"{indicators.get(status, '⚪')} {status}"


def format_usage_trend(trend: str) -> str:
    """
    Add a simple visual indicator to usage trend.
    """

    indicators = {
        "Increasing": "↗",
        "Stable": "→",
        "Declining": "↘",
        "Inactive": "⏸",
    }

    return f"{indicators.get(trend, '•')} {trend}"


def render_risk(risk) -> None:
    """
    Render a single validated RiskFlag.
    """

    severity = risk.severity.value

    severity_class = {
        "High": "severity-high",
        "Medium": "severity-medium",
        "Low": "severity-low",
    }.get(
        severity,
        "severity-low",
    )

    card_class = {
        "High": "sev-high",
        "Medium": "sev-medium",
        "Low": "sev-low",
    }.get(
        severity,
        "sev-low",
    )

    render_html(
        f"""
        <div class="risk-card {card_class}">
            <div class="risk-header">
                <div>
                    <div class="risk-type">{risk.risk_type.value}</div>
                    <div class="risk-ticket">Ticket {risk.ticket_id}</div>
                </div>
                <span class="severity-badge {severity_class}">{severity.upper()}</span>
            </div>
            <div class="risk-label">Why this matters</div>
            <div class="risk-body">{risk.explanation}</div>
            <div class="risk-label">Direct ticket evidence</div>
            <div class="risk-quote">&quot;{risk.evidence_quote}&quot;</div>
            <div class="risk-label">Recommended TAM action</div>
            <div class="risk-body">{risk.recommended_action}</div>
        </div>
        """
    )


def render_talking_point(
    index: int,
    point,
) -> None:
    """
    Render a single TAM talking point.
    """

    render_html(
        f"""
        <div class="talking-point">
            <div class="talking-point-index">{index}</div>
            <div style="flex: 1;">
                <div class="talking-point-title">{point.topic}</div>
                <div class="talking-point-rationale">{point.rationale}</div>
                <div class="talking-point-question">💬 {point.suggested_question}</div>
            </div>
        </div>
        """
    )


def render_account_overview(result) -> None:
    """
    Render account overview and deterministic metrics.
    """

    account = result.account
    metrics = result.metrics

    render_html('<div class="section-title">📁 Account Overview</div>')

    render_html(
        '<div class="section-description">'
        "Deterministic account and support-health indicators used by the "
        "summarisation pipeline."
        "</div>"
    )

    # -------------------------------------------------------------------------
    # Identity row
    # -------------------------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric(
            "Company",
            account.company,
            account.industry,
        )

    with col2:
        render_metric(
            "Plan",
            account.plan_tier,
            f"{account.region} region",
        )

    with col3:
        render_metric(
            "ARR",
            format_currency(account.arr_usd),
            "Annual recurring revenue",
        )

    with col4:
        render_metric(
            "TAM",
            account.tam,
            "Account owner",
        )

    render_html("<div style='height:0.9rem'></div>")

    # -------------------------------------------------------------------------
    # Health row
    # -------------------------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric(
            "Health",
            format_health_status(
                account.health_status.value
            ),
            "Account health status",
        )

    with col2:
        render_metric(
            "Usage Trend",
            format_usage_trend(
                account.usage_trend.value
            ),
            f"{metrics.active_seats:,} / "
            f"{metrics.licensed_seats:,} seats active",
        )

    with col3:
        render_metric(
            "Tickets",
            str(result.ticket_count),
            "Created in selected window",
        )

    with col4:
        render_metric(
            "P1 / P2",
            f"{metrics.p1_tickets_last_90d} / "
            f"{metrics.p2_tickets_last_90d}",
            "Tickets in selected window",
        )

    render_html("<div style='height:0.9rem'></div>")

    # -------------------------------------------------------------------------
    # Customer / renewal row
    # -------------------------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric(
            "Seat Utilization",
            (
                f"{metrics.seat_utilization_percent:.1f}%"
                if metrics.seat_utilization_percent is not None
                else "—"
            ),
            "Active / licensed",
        )

    with col2:
        render_metric(
            "Last Login",
            f"{account.last_login_days_ago} days ago",
            "Customer activity",
        )

    with col3:
        render_metric(
            "Renewal",
            account.renewal_date,
            "Upcoming renewal date",
        )

    with col4:
        nps = (
            str(account.nps_score)
            if account.nps_score is not None
            else "N/A"
        )

        render_metric(
            "NPS",
            nps,
            "Customer sentiment score",
        )


def render_executive_summary(result) -> None:
    """
    Render the executive summary.
    """

    render_html('<div class="section-title">🧭 1. Executive Summary</div>')

    render_html(
        '<div class="section-description">'
        "A concise account-health assessment for QBR preparation."
        "</div>"
    )

    render_html(
        f"""
        <div class="exec-summary-box">
            {result.brief.executive_summary.text}
        </div>
        """
    )


def render_risks(result) -> None:
    """
    Render open risks and flagged issues.
    """

    render_html('<div class="section-title">🚩 2. Open Risks &amp; Flagged Issues</div>')

    render_html(
        '<div class="section-description">'
        "Ticket-level churn and escalation signals supported by direct "
        "evidence from the source ticket."
        "</div>"
    )

    risks = result.brief.open_risks

    if not risks:

        render_html(
            """
            <div class="success-box">
                ✓ No meaningful churn or escalation signals were identified
                in the analyzed ticket history.
            </div>
            """
        )

        return

    # Summary metrics for risks.
    high_count = sum(
        risk.severity.value == "High"
        for risk in risks
    )

    churn_count = sum(
        risk.risk_type.value == "Churn Risk"
        for risk in risks
    )

    escalation_count = sum(
        risk.risk_type.value == "Escalation Signal"
        for risk in risks
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric(
            "Total Flags",
            str(len(risks)),
            "Validated risk signals",
        )

    with col2:
        render_metric(
            "High Severity",
            str(high_count),
            "Requires priority attention",
        )

    with col3:
        render_metric(
            "Churn / Escalation",
            f"{churn_count} / {escalation_count}",
            "Risk classification",
        )

    render_html("<div style='height:0.9rem'></div>")

    for risk in risks:
        render_risk(risk)


def render_talking_points(result) -> None:
    """
    Render recommended TAM talking points.
    """

    render_html('<div class="section-title">💬 3. Recommended Talking Points</div>')

    render_html(
        '<div class="section-description">'
        "Concrete topics and questions the TAM can use during the customer "
        "conversation."
        "</div>"
    )

    points = result.brief.recommended_talking_points

    if not points:

        render_html(
            """
            <div class="empty-box">
                No additional talking points were generated.
            </div>
            """
        )

        return

    for index, point in enumerate(
        points,
        start=1,
    ):
        render_talking_point(
            index=index,
            point=point,
        )


def render_generation_progress(
    account_id: str,
    days: int,
    analysis_date: date,
):
    """
    Execute the streaming summarisation pipeline and render a live,
    styled progress log (a connected timeline) inside a status panel.

    Returns
    -------
    SummarizationResult | None
    """

    result = None
    log_lines: list[str] = []

    with st.status(
        "Generating TAM account brief...",
        expanded=True,
    ) as status:

        # A single placeholder we repaint on every event, so the whole
        # log renders as one cohesive styled timeline instead of a plain
        # scrolling list of st.write() calls.
        log_placeholder = st.empty()

        def repaint() -> None:
            log_placeholder.markdown(
                "\n".join(
                    ['<div class="stream-log">']
                    + [line.strip() for row in log_lines for line in row.strip("\n").splitlines()]
                    + ["</div>"]
                ),
                unsafe_allow_html=True,
            )

        for event in summarize_account_stream(
            account_id=account_id,
            days=days,
            analysis_date=analysis_date,
        ):

            # ---------------------------------------------------------------
            # Progress
            # ---------------------------------------------------------------

            if event.event_type == "started":

                log_lines.append(
                    f"""
                    <div class="stream-row stream-start">
                        <div class="stream-icon">🚀</div>
                        <div class="stream-text">{event.message}</div>
                    </div>
                    """
                )
                repaint()

            elif event.event_type == "progress":

                log_lines.append(
                    f"""
                    <div class="stream-row">
                        <div class="stream-icon">•</div>
                        <div class="stream-text">{event.message}</div>
                    </div>
                    """
                )
                repaint()

            # ---------------------------------------------------------------
            # Final result
            # ---------------------------------------------------------------

            elif event.event_type == "result":

                result = event.data

                log_lines.append(
                    """
                    <div class="stream-row stream-success">
                        <div class="stream-icon">✓</div>
                        <div class="stream-text">Brief compiled successfully</div>
                    </div>
                    """
                )
                repaint()

            # ---------------------------------------------------------------
            # Error
            # ---------------------------------------------------------------

            elif event.event_type == "error":

                status.update(
                    label="Analysis failed",
                    state="error",
                    expanded=True,
                )

                log_lines.append(
                    f"""
                    <div class="stream-row stream-error">
                        <div class="stream-icon">✕</div>
                        <div class="stream-text">{event.message}</div>
                    </div>
                    """
                )
                repaint()

                return None

        # ---------------------------------------------------------------------
        # Completed successfully
        # ---------------------------------------------------------------------

        if result is not None:

            status.update(
                label="Account brief generated",
                state="complete",
                expanded=False,
            )

    return result


# =============================================================================
# Hero
# =============================================================================

render_html(
    """
    <div class="hero">
        <div class="hero-eyebrow">⚡ TAM TOOLKIT</div>
        <div class="hero-title">Account Health Summariser</div>
        <div class="hero-subtitle">
            Turn account context and recent support activity into a
            concise, evidence-based QBR brief.
        </div>
    </div>
    """
)


# =============================================================================
# Sidebar — Analysis controls
# =============================================================================

with st.sidebar:

    st.markdown(
        "## ⚙️ Analysis Controls"
    )

    st.caption(
        "Configure the account health analysis."
    )

    st.divider()

    # -------------------------------------------------------------------------
    # Account ID
    # -------------------------------------------------------------------------

    account_id = st.text_input(
        "Account ID",
        placeholder="e.g. ACC-3336",
        help="Enter the account ID from the account dataset.",
    )

    # -------------------------------------------------------------------------
    # Analysis date
    # -------------------------------------------------------------------------

    today = date.today()

    analysis_date = st.date_input(
        "Analysis date",
        value=today,
        min_value=date(2000, 1, 1),
        max_value=today,
        help=(
            "The analysis window ends on this date. "
            "Only today or a previous date can be selected."
        ),
    )

    # -------------------------------------------------------------------------
    # Number of days
    # -------------------------------------------------------------------------

    days = st.number_input(
        "Total days to look",
        min_value=1,
        value=90,
        step=1,
        help=(
            "Number of days of ticket history to analyze. "
            "Must be a positive number."
        ),
    )

    days = int(days)

    st.divider()

    st.caption(
        f"Analysis window: "
        f"{analysis_date - timedelta(days=days)} → "
        f"{analysis_date}"
    )

    st.caption(
        "Risk evidence is validated against the original ticket body."
    )

    # -------------------------------------------------------------------------
    # Generate button
    # -------------------------------------------------------------------------

    generate = st.button(
        "🚀 Generate Account Brief",
        type="primary",
        use_container_width=True,
    )


# =============================================================================
# Initial state
# =============================================================================

if not generate:

    st.markdown(
        """
### 👋 Ready for your QBR?

Enter an **Account ID**, choose the analysis date and ticket-history
window, then generate the account brief.

The application will:

1. Load the account and relevant ticket history.
2. Analyze account health.
3. Detect churn and escalation signals.
4. Validate direct ticket evidence.
5. Generate actionable TAM talking points.
        """,
    )

    st.info(
        "Tip: the analysis date defaults to today, but you can move it "
        "backward to reproduce historical account health.",
        icon="💡",
    )

    st.stop()


# =============================================================================
# Validate input
# =============================================================================

if not account_id.strip():

    st.error(
        "Please enter an account ID.",
        icon="⚠️",
    )

    st.stop()


if days <= 0:

    st.error(
        "Total days to look must be a positive number.",
        icon="⚠️",
    )

    st.stop()


# Defensive validation even though st.date_input already enforces max_value.
if analysis_date > today:

    st.error(
        "Analysis date cannot be in the future.",
        icon="⚠️",
    )

    st.stop()


# =============================================================================
# Generate
# =============================================================================

result = render_generation_progress(
    account_id=account_id.strip(),
    days=days,
    analysis_date=analysis_date,
)


# =============================================================================
# Render final result
# =============================================================================

if result is None:

    st.stop()


# -------------------------------------------------------------------------
# Account overview
# -------------------------------------------------------------------------

render_account_overview(result)


st.divider()


# -------------------------------------------------------------------------
# Required section 1
# -------------------------------------------------------------------------

render_executive_summary(result)


# -------------------------------------------------------------------------
# Required section 2
# -------------------------------------------------------------------------

render_risks(result)


# -------------------------------------------------------------------------
# Required section 3
# -------------------------------------------------------------------------

render_talking_points(result)


# =============================================================================
# Footer / provenance
# =============================================================================

st.divider()

st.caption(
    f"Analysis generated for {result.account.account_id} · "
    f"{result.account.company} · "
    f"{result.ticket_count} ticket(s) analyzed · "
    f"Analysis date: {analysis_date.isoformat()} · "
    f"Window: {days} days"
)