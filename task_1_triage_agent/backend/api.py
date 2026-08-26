from __future__ import annotations

import asyncio
import json
import sys

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from .schemas import (
    TicketInput,
    TriageResult,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TASK_ROOT = PROJECT_ROOT / "task_1_triage_agent"

CHROMA_DIR = PROJECT_ROOT / "chroma_db"

SETUP_DB_SCRIPT = TASK_ROOT / "setup_db.py"


# ============================================================
# CHROMA COLLECTIONS
# ============================================================

TICKETS_COLLECTION = "historical_tickets"

KNOWLEDGE_COLLECTION = "knowledge_base"


# ============================================================
# GLOBAL APPLICATION STATE
# ============================================================

_agent = None

_db_ready = False

_initialization_complete = False

_initialization_error: str | None = None

_initialization_task: asyncio.Task | None = None


# ============================================================
# INITIALIZATION EVENT STREAM
# ============================================================

# We keep all initialization messages here.
#
# This is better than one global asyncio.Queue because
# multiple SSE clients should be able to see the same
# initialization history.

_initialization_messages: list[dict] = []

_initialization_condition: asyncio.Condition | None = None


# ============================================================
# ADD INITIALIZATION MESSAGE
# ============================================================

async def add_initialization_message(
    event: str,
    message: str,
) -> None:

    global _initialization_condition

    payload = {
        "event": event,
        "message": message,
    }

    _initialization_messages.append(payload)

    if _initialization_condition is not None:

        async with _initialization_condition:

            _initialization_condition.notify_all()


# ============================================================
# SSE HELPER
# ============================================================

def create_sse_message(
    event: str,
    data: dict,
) -> str:

    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, default=str)}\n\n"
    )


# ============================================================
# CHECK CHROMA
# ============================================================

def check_chroma_collections() -> dict:
    """
    Check whether the required Chroma collections exist.

    IMPORTANT:
    This function is called ONLY during application
    initialization.

    It is NOT called for every request.
    """

    try:

        import chromadb

    except ImportError as exc:

        raise RuntimeError(
            "chromadb is not installed."
        ) from exc


    CHROMA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )


    collections = client.list_collections()

    existing_collections = {
        collection.name
        for collection in collections
    }


    tickets_exists = (
        TICKETS_COLLECTION
        in existing_collections
    )

    knowledge_exists = (
        KNOWLEDGE_COLLECTION
        in existing_collections
    )


    return {
        "tickets": tickets_exists,

        "knowledge_base": knowledge_exists,

        "all_ready": (
            tickets_exists
            and knowledge_exists
        ),

        "existing_collections": sorted(
            existing_collections
        ),
    }


# ============================================================
# RUN setup_db.py
# ============================================================

async def run_setup_db() -> None:
    """
    Run setup_db.py exactly once.

    stdout/stderr is converted into initialization
    events which can be consumed by SSE clients.
    """

    if not SETUP_DB_SCRIPT.exists():

        raise RuntimeError(
            f"setup_db.py not found at "
            f"{SETUP_DB_SCRIPT}"
        )


    await add_initialization_message(
        "setup",
        "Starting Chroma database setup...",
    )


    process = await asyncio.create_subprocess_exec(
        sys.executable,

        "-u",

        str(SETUP_DB_SCRIPT),

        cwd=str(TASK_ROOT),

        stdout=asyncio.subprocess.PIPE,

        stderr=asyncio.subprocess.STDOUT,
    )


    assert process.stdout is not None


    while True:

        line = await process.stdout.readline()

        if not line:

            break


        message = line.decode(
            errors="replace"
        ).strip()


        if message:

            await add_initialization_message(
                "setup",
                message,
            )


    return_code = await process.wait()


    if return_code != 0:

        raise RuntimeError(
            f"setup_db.py failed with "
            f"exit code {return_code}"
        )


    await add_initialization_message(
        "setup_complete",
        "Chroma database setup completed successfully.",
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

async def initialize_database() -> None:
    """
    Initialize Chroma exactly once when FastAPI starts.
    """

    global _db_ready


    await add_initialization_message(
        "setup",
        "Checking Chroma collections...",
    )


    status = await asyncio.to_thread(
        check_chroma_collections
    )


    # --------------------------------------------------------
    # Already initialized
    # --------------------------------------------------------

    if status["all_ready"]:

        await add_initialization_message(
            "setup",
            "Historical tickets collection found.",
        )

        await add_initialization_message(
            "setup",
            "Knowledge base collection found.",
        )

        await add_initialization_message(
            "ready",
            "Both Chroma collections are ready.",
        )

        _db_ready = True

        return


    # --------------------------------------------------------
    # Missing collections
    # --------------------------------------------------------

    if not status["tickets"]:

        await add_initialization_message(
            "setup",
            "Historical tickets collection is missing.",
        )


    if not status["knowledge_base"]:

        await add_initialization_message(
            "setup",
            "Knowledge base collection is missing.",
        )


    # --------------------------------------------------------
    # Build database
    # --------------------------------------------------------

    await run_setup_db()


    # --------------------------------------------------------
    # Verify ONCE after setup
    # --------------------------------------------------------

    await add_initialization_message(
        "setup",
        "Verifying Chroma collections...",
    )


    final_status = await asyncio.to_thread(
        check_chroma_collections
    )


    if not final_status["all_ready"]:

        raise RuntimeError(
            "setup_db.py completed but the required "
            "Chroma collections were not created."
        )


    await add_initialization_message(
        "ready",
        "Both Chroma collections verified successfully.",
    )


    _db_ready = True


# ============================================================
# LOAD AGENT
# ============================================================

def load_agent():
    """
    Import and load the LangGraph agent.

    IMPORTANT:
    agent.py is imported ONLY after Chroma is ready.
    """

    global _agent


    if _agent is not None:

        return _agent


    print(
        "Loading LangGraph triage agent..."
    )


    # IMPORTANT:
    #
    # Do NOT import agent.py at the top of api.py.
    #
    # It is imported only after database initialization.

    from .agent import triage_agent


    _agent = triage_agent


    print(
        "LangGraph triage agent loaded."
    )


    return _agent


# ============================================================
# INITIALIZE APPLICATION
# ============================================================

async def initialize_application() -> None:
    """
    Complete application initialization.

    Order:

        1. Chroma
        2. Agent

    This function runs exactly once when the FastAPI
    process starts.
    """

    global _initialization_complete
    global _initialization_error


    try:

        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        await initialize_database()


        # ----------------------------------------------------
        # AGENT
        # ----------------------------------------------------

        await add_initialization_message(
            "setup",
            "Initializing LangGraph triage agent...",
        )


        await asyncio.to_thread(
            load_agent
        )


        await add_initialization_message(
            "ready",
            "LangGraph triage agent is ready.",
        )


        _initialization_complete = True


        await add_initialization_message(
            "complete",
            "Application initialization completed.",
        )


    except Exception as exc:

        _initialization_error = str(exc)

        await add_initialization_message(
            "error",
            f"Application initialization failed: {exc}",
        )


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    global _initialization_task
    global _initialization_condition


    # --------------------------------------------------------
    # Create condition
    # --------------------------------------------------------

    _initialization_condition = (
        asyncio.Condition()
    )


    # --------------------------------------------------------
    # Start initialization in background
    #
    # IMPORTANT:
    #
    # We DON'T await it here.
    #
    # This allows:
    #
    #     POST /triage/stream
    #
    # to connect while setup_db.py is running.
    # --------------------------------------------------------

    _initialization_task = asyncio.create_task(
        initialize_application()
    )


    yield


    # --------------------------------------------------------
    # Shutdown
    # --------------------------------------------------------

    if _initialization_task is not None:

        if not _initialization_task.done():

            _initialization_task.cancel()

            try:

                await _initialization_task

            except asyncio.CancelledError:

                pass


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Intelligent Ticket Triage Agent",

    description=(
        "LangGraph + RAG based "
        "Intelligent Ticket Triage Agent"
    ),

    version="1.0.0",

    lifespan=lifespan,
)


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": (
            "ready"
            if _initialization_complete
            else "initializing"
        ),

        "database": _db_ready,

        "agent_loaded": (
            _agent is not None
        ),

        "initialization_error":
            _initialization_error,
    }


# ============================================================
# WAIT FOR INITIALIZATION
# ============================================================

async def wait_for_initialization() -> None:
    """
    Used by the normal /triage endpoint.

    Unlike SSE, the normal endpoint waits until the
    application is ready.
    """

    if _initialization_complete:

        return


    if _initialization_error:

        raise RuntimeError(
            _initialization_error
        )


    if _initialization_task is None:

        raise RuntimeError(
            "Application initialization task "
            "has not been started."
        )


    try:

        await _initialization_task

    except Exception as exc:

        raise RuntimeError(
            f"Application initialization failed: {exc}"
        ) from exc


    if _initialization_error:

        raise RuntimeError(
            _initialization_error
        )


# ============================================================
# NORMAL TRIAGE
# ============================================================

@app.post(
    "/triage",
    response_model=TriageResult,
)
async def triage(
    ticket: TicketInput,
) -> TriageResult:

    # --------------------------------------------------------
    # Wait for startup initialization
    # --------------------------------------------------------

    try:

        await wait_for_initialization()

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


    # --------------------------------------------------------
    # Agent
    # --------------------------------------------------------

    if _agent is None:

        raise HTTPException(
            status_code=500,
            detail="Triage agent is not initialized.",
        )


    # --------------------------------------------------------
    # Run LangGraph
    # --------------------------------------------------------

    try:

        result = await asyncio.to_thread(
            _agent.invoke,
            {
                "ticket": ticket,
            },
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Triage execution failed: "
                f"{exc}"
            ),
        )


    # --------------------------------------------------------
    # Return structured result
    # --------------------------------------------------------

    return result["final_result"]


# ============================================================
# STREAMING TRIAGE
# ============================================================

@app.post("/triage/stream")
async def triage_stream(
    ticket: TicketInput,
):

    async def event_generator() -> AsyncGenerator[
        str,
        None,
    ]:

        # ====================================================
        # REQUEST RECEIVED
        # ====================================================

        yield create_sse_message(
            "status",
            {
                "message": "Triage request received."
            },
        )


        # ====================================================
        # STREAM APPLICATION INITIALIZATION
        # ====================================================

        message_index = 0


        while True:

            # ------------------------------------------------
            # Send all messages that haven't been sent
            # ------------------------------------------------

            while (
                message_index
                < len(_initialization_messages)
            ):

                message = (
                    _initialization_messages[
                        message_index
                    ]
                )

                message_index += 1


                yield create_sse_message(
                    message["event"],
                    {
                        "message":
                            message["message"],
                    },
                )


            # ------------------------------------------------
            # Initialization failed
            # ------------------------------------------------

            if _initialization_error:

                return


            # ------------------------------------------------
            # Initialization complete
            # ------------------------------------------------

            if _initialization_complete:

                break


            # ------------------------------------------------
            # Wait for another initialization message
            # ------------------------------------------------

            if _initialization_condition is not None:

                async with _initialization_condition:

                    try:

                        await asyncio.wait_for(
                            _initialization_condition.wait(),
                            timeout=1.0,
                        )

                    except asyncio.TimeoutError:

                        # SSE heartbeat

                        yield create_sse_message(
                            "heartbeat",
                            {
                                "message":
                                    "Application is initializing..."
                            },
                        )

            else:

                await asyncio.sleep(0.2)


        # ====================================================
        # APPLICATION READY
        # ====================================================

        yield create_sse_message(
            "status",
            {
                "message":
                    "Triage agent ready.",
            },
        )


        # ====================================================
        # START TRIAGE
        # ====================================================

        yield create_sse_message(
            "start",
            {
                "message":
                    "Starting ticket analysis...",
            },
        )


        # ====================================================
        # LANGGRAPH STREAM
        # ====================================================

        try:

            # Import lazily.
            #
            # This guarantees agent.py was imported only
            # after Chroma initialization.

            from .agent import (
                triage_ticket_stream
            )


            async for event in triage_ticket_stream(
                ticket
            ):

                event_type = event.get(
                    "event",
                    "progress",
                )


                # --------------------------------------------
                # START
                # --------------------------------------------

                if event_type == "start":

                    yield create_sse_message(
                        "start",
                        {
                            "message":
                                event.get(
                                    "message",
                                    "Triage started.",
                                ),
                        },
                    )


                # --------------------------------------------
                # PROGRESS
                # --------------------------------------------

                elif event_type == "progress":

                    yield create_sse_message(
                        "progress",
                        {
                            "node":
                                event.get("node"),

                            "message":
                                event.get(
                                    "message",
                                    "Processing...",
                                ),
                        },
                    )


                # --------------------------------------------
                # NODE COMPLETE
                # --------------------------------------------

                elif event_type == "node_complete":

                    yield create_sse_message(
                        "node_complete",
                        {
                            "node":
                                event.get("node"),

                            "message":
                                event.get(
                                    "message",
                                    "Step completed.",
                                ),
                        },
                    )


                # --------------------------------------------
                # RESULT
                # --------------------------------------------

                elif event_type == "result":

                    yield create_sse_message(
                        "result",
                        {
                            "data":
                                event['data'],
                        },
                    )


                # --------------------------------------------
                # DONE
                # --------------------------------------------

                elif event_type == "done":

                    yield create_sse_message(
                        "done",
                        {
                            "message":
                                event.get(
                                    "message",
                                    "Triage completed successfully.",
                                ),
                        },
                    )


                # --------------------------------------------
                # ERROR
                # --------------------------------------------

                elif event_type == "error":

                    yield create_sse_message(
                        "error",
                        {
                            "message":
                                event.get(
                                    "message",
                                    "Triage failed.",
                                ),
                        },
                    )

                    return


                # --------------------------------------------
                # UNKNOWN
                # --------------------------------------------

                else:

                    yield create_sse_message(
                        "progress",
                        {
                            "message":
                                event.get(
                                    "message",
                                    "Processing...",
                                ),
                        },
                    )


        except Exception as exc:

            yield create_sse_message(
                "error",
                {
                    "message":
                        f"Triage failed: {exc}",
                },
            )

            return


        # ====================================================
        # SAFETY DONE
        # ====================================================

        yield create_sse_message(
            "done",
            {
                "message":
                    "Triage completed successfully.",
            },
        )


    # ========================================================
    # SSE RESPONSE
    # ========================================================

    return StreamingResponse(
        event_generator(),

        media_type="text/event-stream",

        headers={
            "Cache-Control":
                "no-cache",

            "Connection":
                "keep-alive",

            "X-Accel-Buffering":
                "no",

            "Content-Type":
                "text/event-stream",
        },
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "name":
            "Intelligent Ticket Triage Agent",

        "status":
            (
                "ready"
                if _initialization_complete
                else "initializing"
            ),

        "endpoints": {
            "health":
                "/health",

            "triage":
                "/triage",

            "stream":
                "/triage/stream",
        },
    }