"""Streamlit frontend for the Intelligent Ticket Triage system.

Talks to a local FastAPI backend (LangGraph + hybrid RAG pipeline) over
SSE and renders live agent progress plus the final triage result.
"""

from __future__ import annotations

import ast
import atexit
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

import requests
import streamlit as st

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("triage_ui")


# ============================================================
# CONFIG
# ============================================================

API_HOST = os.getenv("TRIAGE_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("TRIAGE_API_PORT", "8000"))
API_URL = f"http://{API_HOST}:{API_PORT}"
STREAM_URL = f"{API_URL}/triage/stream"
BACKEND_START_TIMEOUT_S = 15
STREAM_TIMEOUT_S = (10, 300)  # (connect, read)

PIPELINE_STEPS = [
    "Preparing ticket",
    "Searching historical tickets",
    "Searching knowledge base",
    "Running hybrid retrieval",
    "Reranking evidence",
    "Evaluating evidence",
    "Refining retrieval if necessary",
    "Generating final triage",
]

# Maps SSE "node" identifiers from the backend to an index in PIPELINE_STEPS.
NODE_STEP_INDEX = {
    "prepare_ticket": 0,
    "retrieve": 1,
    "refine_query": 6,
    "assess_evidence": 5,
    "final_reasoning": 7,
}

URGENCY_BADGE_CLASS = {
    "P1": "badge-red",
    "P2": "badge-yellow",
    "P3": "badge-purple",
    "P4": "badge-green",
}

st.set_page_config(
    page_title="Intelligent Ticket Triage",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# STYLES
# ============================================================

CSS = """
<style>
.stApp {
    background:
        radial-gradient(circle at 10% 0%, rgba(99, 102, 241, 0.12), transparent 30%),
        radial-gradient(circle at 90% 5%, rgba(14, 165, 233, 0.08), transparent 28%),
        #070b14;
    color: #f1f5f9;
}
.block-container { max-width: 1250px; padding-top: 2rem; padding-bottom: 4rem; }

.hero {
    padding: 35px 38px;
    border-radius: 24px;
    border: 1px solid #202b42;
    background: linear-gradient(135deg, rgba(99,102,241,.16), rgba(15,23,42,.94));
    box-shadow: 0 25px 80px rgba(0,0,0,.30);
    margin-bottom: 22px;
}
.hero-label { color: #818cf8; font-size: .75rem; font-weight: 800; letter-spacing: .15em; text-transform: uppercase; margin-bottom: 10px; }
.hero-title { font-size: 2.25rem; font-weight: 850; color: #f8fafc; margin: 0; }
.hero-subtitle { color: #94a3b8; max-width: 760px; line-height: 1.65; margin-top: 12px; font-size: .98rem; }

.backend-status {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 7px 13px; border-radius: 999px;
    background: rgba(34,197,94,.08); border: 1px solid rgba(34,197,94,.25);
    color: #86efac; font-size: .78rem; font-weight: 750; margin-bottom: 22px;
}
.backend-dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 12px rgba(34,197,94,.8); }

.card { background: rgba(15,23,42,.78); border: 1px solid #202b42; border-radius: 18px; padding: 22px; box-shadow: 0 12px 45px rgba(0,0,0,.18); }
.card-title { font-size: 1.05rem; font-weight: 800; color: #f8fafc; margin-bottom: 4px; }
.card-subtitle { color: #7f8da6; font-size: .8rem; line-height: 1.5; margin-bottom: 18px; }

/* Input / textarea theming. Streamlit/BaseWeb markup varies across versions,
   so we target every selector that has matched in the wild and force with
   !important to beat the injected light-theme defaults. */
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="base-input"],
.stTextInput > div > div,
.stTextArea > div > div {
    background-color: #0b1220 !important;
    border-color: #26334c !important;
    border-radius: 11px !important;
}
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {
    background-color: #0b1220 !important;
    color: #f1f5f9 !important;
    -webkit-text-fill-color: #f1f5f9 !important;
    caret-color: #f1f5f9 !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #56647c !important;
    -webkit-text-fill-color: #56647c !important;
    opacity: 1 !important;
}
.stSelectbox div[data-baseweb="select"] * { color: #f1f5f9 !important; }
label, .stCaption, [data-testid="stCaptionContainer"] { color: #a5b1c7 !important; font-size: .8rem !important; font-weight: 700 !important; }

.stButton > button {
    width: 100%; min-height: 48px; border-radius: 12px; border: 1px solid #6366f1;
    color: white; font-weight: 800;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    box-shadow: 0 12px 30px rgba(79,70,229,.25);
}
.stButton > button:disabled { opacity: .45; box-shadow: none; }

.progress-container { background: #0b1220; border: 1px solid #202b42; border-radius: 18px; padding: 18px 18px 20px; margin-top: 12px; }
.progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.progress-title { color: #f8fafc; font-size: .9rem; font-weight: 800; }
.progress-count { color: #56647c; font-size: .74rem; font-weight: 700; margin-left: 8px; }
.progress-live { display: inline-flex; align-items: center; gap: 6px; color: #38bdf8; font-size: .68rem; font-weight: 850; letter-spacing: .1em; }
.progress-live-dot { width: 6px; height: 6px; border-radius: 50%; background: #38bdf8; animation: pulse-dot 1.2s ease-in-out infinite; }
.progress-bar-track { height: 5px; border-radius: 999px; background: #182238; margin: 12px 0 16px; overflow: hidden; }
.progress-bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #6366f1, #38bdf8); transition: width .35s ease; }

.step { display: flex; align-items: center; gap: 12px; padding: 9px 10px; margin: 2px 0; border-radius: 10px; color: #4b5875; }
.step-active { background: rgba(99,102,241,.12); border: 1px solid rgba(99,102,241,.22); color: #e0e7ff; }
.step-done { color: #8fb3a3; }
.step-num {
    width: 20px; height: 20px; flex-shrink: 0; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: .65rem; font-weight: 800; background: #1a2540; color: #56647c;
}
.step-active .step-num { background: #6366f1; color: #fff; box-shadow: 0 0 0 4px rgba(99,102,241,.18); }
.step-done .step-num { background: #16532f; color: #86efac; }
.step-label { flex: 1; font-size: .84rem; font-weight: 650; }
.step-active .step-message { display: block; color: #93a3c2; font-size: .72rem; font-weight: 500; margin-top: 2px; font-style: italic; }
.step-message { display: none; }

@keyframes pulse-dot { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: .35; transform: scale(.7); } }

.section-title { font-size: 1.15rem; font-weight: 850; color: #f8fafc; margin-top: 26px; margin-bottom: 12px; }
.metric { background: #0c1424; border: 1px solid #202b42; border-radius: 15px; padding: 17px; min-height: 90px; }
.metric-label { color: #71809a; font-size: .68rem; text-transform: uppercase; letter-spacing: .08em; font-weight: 800; }
.metric-value { color: #f8fafc; font-size: 1rem; font-weight: 850; margin-top: 7px; }

.badge { display: inline-block; padding: 5px 10px; border-radius: 999px; font-size: .7rem; font-weight: 800; margin-right: 5px; border: 1px solid; }
.badge-purple { color: #c4b5fd; background: rgba(139,92,246,.08); border-color: rgba(139,92,246,.25); }
.badge-yellow { color: #fde68a; background: rgba(234,179,8,.08); border-color: rgba(234,179,8,.25); }
.badge-red { color: #fda4af; background: rgba(244,63,94,.08); border-color: rgba(244,63,94,.25); }
.badge-green { color: #86efac; background: rgba(34,197,94,.08); border-color: rgba(34,197,94,.25); }

.evidence { background: #0b1220; border: 1px solid #202b42; border-radius: 14px; padding: 15px; margin-bottom: 9px; }
.evidence-row { display: flex; justify-content: space-between; }
.evidence-title { color: #e2e8f0; font-size: .85rem; font-weight: 800; }
.evidence-score { color: #a5b4fc; font-weight: 800; }
.evidence-meta { color: #71809a; font-size: .74rem; margin-top: 5px; line-height: 1.6; }
.evidence-text { color: #b8c4d8; line-height: 1.65; font-size: .82rem; margin-top: 10px; }

.response { background: linear-gradient(135deg, rgba(99,102,241,.06), rgba(14,165,233,.04)); border: 1px solid #263653; border-radius: 16px; padding: 20px; color: #dbe4f2; line-height: 1.75; white-space: pre-wrap; }

.footer { text-align: center; color: #475569; font-size: .7rem; padding-top: 35px; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# ============================================================
# SMALL HTML HELPERS
# ============================================================

def esc(value: Any) -> str:
    """HTML-escape a value for safe interpolation into markdown blocks."""
    if value is None:
        return ""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def fmt_score(value: Any) -> str:
    return f"{float(value):.3f}" if isinstance(value, (float, int)) else "N/A"


def badge_html(label: str, value: Any, variant: str = "purple") -> str:
    return f'<span class="badge badge-{variant}">{esc(label)} · {esc(value)}</span>'


def metric_html(label: str, value: Any) -> str:
    return (
        f'<div class="metric"><div class="metric-label">{esc(label)}</div>'
        f'<div class="metric-value">{esc(value)}</div></div>'
    )


def evidence_html(
    title: str,
    meta: str = "",
    text: str = "",
    score: Any = None,
) -> str:
    """Render one evidence-style card. `meta` and `title` may contain pre-escaped HTML."""
    score_html = f'<div class="evidence-score">{esc(fmt_score(score))}</div>' if score is not None else ""
    meta_html = f'<div class="evidence-meta">{meta}</div>' if meta else ""
    text_html = f'<div class="evidence-text">{esc(text)}</div>' if text else ""
    return (
        '<div class="evidence">'
        f'<div class="evidence-row"><div class="evidence-title">{title}</div>{score_html}</div>'
        f"{meta_html}{text_html}"
        "</div>"
    )


def progress_html(
    steps: list[str],
    current_step: int,
    completed: set[int],
    activity_message: str = "",
) -> str:
    rows = []
    for index, step in enumerate(steps):
        if index in completed:
            state, marker = "step-done", "✓"
        elif index == current_step:
            state, marker = "step-active", str(index + 1)
        else:
            state, marker = "", str(index + 1)

        message_html = (
            f'<div class="step-message">{esc(activity_message)}</div>'
            if state == "step-active" and activity_message
            else ""
        )
        rows.append(
            f'<div class="step {state}">'
            f'<div class="step-num">{marker}</div>'
            f'<div style="flex:1"><div class="step-label">{esc(step)}</div>{message_html}</div>'
            "</div>"
        )

    pct = int(round(100 * len(completed) / len(steps))) if steps else 0

    return (
        '<div class="progress-container">'
        '<div class="progress-header">'
        f'<div><span class="progress-title">Agent execution</span>'
        f'<span class="progress-count">{len(completed)}/{len(steps)} steps</span></div>'
        '<div class="progress-live"><span class="progress-live-dot"></span>LIVE</div>'
        "</div>"
        f'<div class="progress-bar-track"><div class="progress-bar-fill" style="width:{pct}%"></div></div>'
        f'{"".join(rows)}'
        "</div>"
    )


# ============================================================
# BACKEND LIFECYCLE
# ============================================================

@st.cache_resource
def start_backend() -> tuple[subprocess.Popen | None, bool]:
    """Start the FastAPI backend if it isn't already running. Returns (process, is_online)."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=1.5)
        if response.ok:
            return None, True
    except requests.RequestException:
        pass

    project_dir = os.path.dirname(os.path.abspath(__file__))
    command = [
        sys.executable, "-m", "uvicorn", "backend.api:app",
        "--host", API_HOST, "--port", str(API_PORT),
    ]

    try:
        process = subprocess.Popen(
            command,
            cwd=project_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        logger.exception("Failed to launch FastAPI backend")
        return None, False

    atexit.register(_terminate_backend, process)

    deadline = time.time() + BACKEND_START_TIMEOUT_S
    while time.time() < deadline:
        try:
            response = requests.get(f"{API_URL}/health", timeout=1)
            if response.ok:
                return process, True
        except requests.RequestException:
            time.sleep(0.25)

    logger.warning("Backend did not report healthy within %ss", BACKEND_START_TIMEOUT_S)
    return process, False


def _terminate_backend(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    logger.info("Shutting down backend subprocess (pid=%s)", process.pid)
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()

_STEP_KEYWORDS: list[tuple[int, tuple[str, ...]]] = [
    (0, ("prepar", "normalis", "normaliz")),
    (1, ("historical ticket", "similar ticket", "ticket search")),
    (2, ("knowledge base", "kb search", "kb retriev")),
    (3, ("hybrid", "retriev")),
    (4, ("rerank",)),
    (5, ("assess", "evaluat")),
    (6, ("refin",)),
    (7, ("final", "triage", "reason", "classif")),
]


def infer_step_index(node: str | None, message: str) -> int | None:
    """Map an SSE event to a pipeline step. Prefers an exact `node` id match,
    falls back to keyword matching against the node id / message so the
    progress panel still advances sensibly even if the backend's node names
    don't line up with NODE_STEP_INDEX exactly."""
    if node in NODE_STEP_INDEX:
        return NODE_STEP_INDEX[node]

    haystack = f"{node or ''} {message or ''}".lower()
    for index, keywords in _STEP_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return index
    return None


# ============================================================
# SSE PARSING
# ============================================================

def parse_sse(response: requests.Response) -> Iterator[tuple[str, dict]]:
    """Yield (event_name, data) pairs from a text/event-stream response."""
    event_name = None
    data_lines: list[str] = []

    for raw_line in response.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue
        line = raw_line.strip()

        if line == "":
            if event_name or data_lines:
                raw_data = "\n".join(data_lines)
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    data = {"message": raw_data}
                yield event_name or "message", data
            event_name, data_lines = None, []
            continue

        if line.startswith("event:"):
            event_name = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())


# ============================================================
# TRIAGE RUN STATE (persisted across Streamlit reruns)
# ============================================================

@dataclass
class TriageRunState:
    result: dict | None = None
    completed_steps: set[int] = field(default_factory=set)
    current_step: int = 0
    error: str | None = None
    finished: bool = False


def get_run_state() -> TriageRunState:
    if "triage_run" not in st.session_state:
        st.session_state.triage_run = TriageRunState()
    return st.session_state.triage_run


def build_payload(
    subject: str,
    body: str,
    ticket_id: str,
    account_id: str,
    company: str,
    product: str,
    channel: str,
    plan_tier: str,
) -> dict:
    payload = {"subject": subject.strip(), "body": body.strip()}
    optional = {
        "ticket_id": ticket_id.strip(),
        "account_id": account_id.strip(),
        "company": company.strip(),
        "product": product.strip(),
    }
    payload.update({key: value for key, value in optional.items() if value})

    if channel != "Not specified":
        payload["channel"] = channel
    if plan_tier != "Not specified":
        payload["plan_tier"] = plan_tier

    return payload


def validate_ticket(subject: str, body: str) -> list[str]:
    errors = []
    if not subject.strip():
        errors.append("Subject is required.")
    elif len(subject.strip()) < 5:
        errors.append("Subject must contain at least 5 characters.")

    if not body.strip():
        errors.append("Ticket body is required.")
    elif len(body.strip()) < 20:
        errors.append("Ticket body must contain at least 20 characters.")

    return errors


# ============================================================
# RESULT RENDERING
# ============================================================

def render_result(result: dict) -> None:
    if not isinstance(result, dict):
        st.error("Invalid result received from backend.")
        return

    st.markdown('<div class="section-title">🎯 Triage Decision</div>', unsafe_allow_html=True)

    urgency = str(result.get("urgency", "Unknown"))
    urgency_class = URGENCY_BADGE_CLASS.get(urgency, "badge-purple")
    st.markdown(
        badge_html("Product Area", result.get("product_area"))
        + badge_html("Category", result.get("category"))
        + badge_html("Priority", urgency, variant=urgency_class.removeprefix("badge-")),
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    metrics = [
        ("Product Area", result.get("product_area", "Unknown")),
        ("Issue Category", result.get("category", "Unknown")),
        ("Recommended Team", result.get("recommended_team", "Unknown")),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(metric_html(label, value), unsafe_allow_html=True)

    st.markdown('<div class="section-title">🧠 Agent Reasoning</div>', unsafe_allow_html=True)
    st.markdown(
        evidence_html("Why was this ticket classified this way?", text=result.get("reasoning", "")),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">📚 Knowledge Base Match</div>', unsafe_allow_html=True)
    kb = result.get("knowledge_base_match")
    if result.get("known_issue") and isinstance(kb, dict):
        meta = (
            f'Source: <b>{esc(kb.get("source"))}</b> &nbsp;·&nbsp; '
            f'Section: <b>{esc(kb.get("section"))}</b> &nbsp;·&nbsp; '
            f'Relevance: <b>{esc(fmt_score(kb.get("relevance_score")))}</b>'
        )
        st.markdown(
            evidence_html("✓ Known issue detected", meta=meta, text=kb.get("excerpt", "")),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            evidence_html(
                "No confirmed known issue",
                meta="The retrieval pipeline did not find sufficiently strong knowledge-base evidence for a confirmed known-issue match.",
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">🔎 Historical Ticket Evidence</div>', unsafe_allow_html=True)
    similar = result.get("similar_tickets", [])
    if similar:
        for ticket in similar:
            meta = " &nbsp;·&nbsp; ".join(
                esc(ticket.get(field, ""))
                for field in ("product", "product_area", "category", "urgency", "status")
            )
            st.markdown(
                evidence_html(
                    esc(ticket.get("ticket_id")),
                    meta=meta,
                    score=ticket.get("similarity_score"),
                ),
                unsafe_allow_html=True,
            )
    else:
        st.info("No similar historical tickets found.")

    st.markdown('<div class="section-title">✉️ Suggested First Response</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="response">{esc(result.get("draft_response", ""))}</div>', unsafe_allow_html=True)

    with st.expander("View structured JSON"):
        st.json(result)


# ============================================================
# LAYOUT: HERO + STATUS
# ============================================================

def render_hero(backend_online: bool) -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-label">AI SUPPORT OPERATIONS</div>
            <div class="hero-title">🎯 Intelligent Ticket Triage</div>
            <div class="hero-subtitle">
                Automatically classify, prioritise, retrieve supporting evidence,
                detect known issues and route incoming support tickets using
                LangGraph + Hybrid RAG.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if backend_online:
        st.markdown(
            '<div class="backend-status"><span class="backend-dot"></span>'
            "Triage backend online</div>",
            unsafe_allow_html=True,
        )
    else:
        st.error(f"FastAPI backend is unavailable at {API_URL}")


def render_pipeline_explainer() -> None:
    steps = [
        ("01 · Prepare ticket", "Normalise subject and body."),
        ("02 · Hybrid retrieval", "Semantic + lexical retrieval from tickets and knowledge base."),
        ("03 · Reranking", "Select the strongest evidence."),
        ("04 · Multi-hop reasoning", "Refine retrieval when evidence is insufficient."),
        ("05 · Final triage", "Classification, priority, routing and response."),
    ]
    cards = "".join(evidence_html(title, meta=meta) for title, meta in steps)
    st.markdown(
        '<div class="card"><div class="card-title">🧠 Agent Pipeline</div>'
        '<div class="card-subtitle">The request flows through the LangGraph triage pipeline.</div>'
        f"{cards}</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# STREAMING RUN
# ============================================================

def run_triage(payload: dict, progress_ph) -> TriageRunState:
    """Stream the triage pipeline and return the final run state. Mutates the placeholder live."""
    state = TriageRunState()
    last_message = ""

    def refresh_progress() -> None:
        progress_ph.markdown(
            progress_html(PIPELINE_STEPS, state.current_step, state.completed_steps, last_message),
            unsafe_allow_html=True,
        )

    refresh_progress()

    try:
        with requests.post(
            STREAM_URL,
            json=payload,
            stream=True,
            timeout=STREAM_TIMEOUT_S,
            headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
        ) as response:
            response.raise_for_status()

            for event_type, data in parse_sse(response):
                if event_type in ("status", "start", "progress"):
                    node = data.get("node")
                    last_message = data.get("message", "Processing...")
                    inferred = infer_step_index(node, last_message)
                    if inferred is not None:
                        state.current_step = inferred
                    refresh_progress()

                elif event_type == "node_complete":
                    node = data.get("node")
                    inferred = infer_step_index(node, last_message)
                    if inferred is not None:
                        state.completed_steps.add(inferred)
                        state.current_step = min(inferred + 1, len(PIPELINE_STEPS) - 1)
                    refresh_progress()

                elif event_type == "result":
                    result_data = data.get("data")
                    if isinstance(result_data, dict) and state.result is None:
                        state.result = result_data
                        state.completed_steps = set(range(len(PIPELINE_STEPS)))
                        state.current_step = len(PIPELINE_STEPS) - 1
                        last_message = "Done."
                        refresh_progress()

                elif event_type == "error":
                    state.error = data.get("message", "Triage failed.")
                    break

                elif event_type == "done":
                    state.completed_steps = set(range(len(PIPELINE_STEPS)))
                    state.current_step = len(PIPELINE_STEPS) - 1
                    last_message = "Done."
                    refresh_progress()

    except requests.exceptions.ConnectionError:
        state.error = f"Could not connect to FastAPI at {API_URL}."
    except requests.exceptions.Timeout:
        state.error = "Triage request timed out."
    except requests.exceptions.HTTPError as exc:
        state.error = f"FastAPI returned an error: {exc}"
    except Exception as exc:  # noqa: BLE001 - surface unexpected errors to the user
        logger.exception("Unexpected error during triage run")
        state.error = f"Unexpected error: {exc}"

    state.finished = True
    return state


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    inject_css()

    backend_process, backend_online = start_backend()
    render_hero(backend_online)

    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown(
            '<div class="card"><div class="card-title">📝 Incoming Support Ticket</div>'
            '<div class="card-subtitle">Provide the customer\'s subject and message. '
            "Optional metadata can be supplied when available.</div></div>",
            unsafe_allow_html=True,
        )

        subject = st.text_input("Subject", max_chars=300, placeholder="Unable to connect DataBridge Pro to Connectors")
        st.caption(f"{len(subject)} / 300 characters")

        body = st.text_area("Ticket body", height=300, max_chars=10000, placeholder=(
            "Describe the customer's issue, error message, impact, environment..."
        ))
        st.caption(f"{len(body)} / 10,000 characters")

        with st.expander("Optional ticket context"):
            col1, col2 = st.columns(2)
            with col1:
                ticket_id = st.text_input("Ticket ID", placeholder="TKT-10042")
                account_id = st.text_input("Account ID", placeholder="ACC-3847")
                company = st.text_input("Company", placeholder="Initech")
            with col2:
                product = st.text_input("Product", placeholder="DataBridge Pro")
                channel = st.selectbox("Channel", ["Not specified", "email", "portal", "chat", "phone"])
                plan_tier = st.selectbox(
                    "Plan tier", ["Not specified", "Starter", "Professional", "Business", "Enterprise"]
                )

        button_cols = st.columns([3, 1])
        with button_cols[0]:
            run_clicked = st.button("🚀 Run Intelligent Triage", type="primary", disabled=not backend_online)
        with button_cols[1]:
            if st.button("Clear", disabled=get_run_state().result is None and get_run_state().error is None):
                st.session_state.triage_run = TriageRunState()
                st.rerun()

    with right:
        render_pipeline_explainer()

    if run_clicked:
        errors = validate_ticket(subject, body)
        if errors:
            for error in errors:
                st.error(error)
        else:
            payload = build_payload(subject, body, ticket_id, account_id, company, product, channel, plan_tier)

            st.markdown('<div class="section-title">⚡ Live Agent Execution</div>', unsafe_allow_html=True)
            progress_ph = st.empty()

            run_state = run_triage(payload, progress_ph)
            st.session_state.triage_run = run_state

    # Render whatever the latest completed/errored run produced. This lives
    # outside `if run_clicked` so it survives reruns triggered by unrelated
    # widget interactions (expanders, the JSON viewer, etc.).
    state = get_run_state()
    if state.finished and not run_clicked:
        st.markdown('<div class="section-title">⚡ Live Agent Execution</div>', unsafe_allow_html=True)
        st.markdown(
            progress_html(
                PIPELINE_STEPS,
                state.current_step,
                state.completed_steps,
                "Done." if state.result else (state.error or ""),
            ),
            unsafe_allow_html=True,
        )

    if state.error:
        st.error(f"❌ {state.error}")
    if state.result:
        render_result(state.result)

    st.markdown(
        '<div class="footer">Intelligent Ticket Triage &nbsp;·&nbsp; LangGraph '
        "&nbsp;·&nbsp; Hybrid RAG &nbsp;·&nbsp; FastAPI &nbsp;·&nbsp; SSE</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()