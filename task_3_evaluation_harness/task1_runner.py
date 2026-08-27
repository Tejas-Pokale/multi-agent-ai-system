# evals/task1_runner.py

from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


TASK1_BASE_URL = os.getenv(
    "TASK1_BASE_URL",
    "http://127.0.0.1:8000",
)

TASK1_ENDPOINT = os.getenv(
    "TASK1_ENDPOINT",
    "/triage",
)

TASK1_TIMEOUT = int(
    os.getenv(
        "TASK1_TIMEOUT_SECONDS",
        "180",
    )
)


def run_task1_case(
    input_data: dict[str, Any],
) -> tuple[dict[str, Any], float]:
    """
    Execute Task 1 through the real synchronous FastAPI endpoint.

    Returns:
        (response_json, latency_seconds)
    """

    url = (
        TASK1_BASE_URL.rstrip("/")
        + "/"
        + TASK1_ENDPOINT.lstrip("/")
    )

    start = time.perf_counter()

    try:
        response = requests.post(
            url,
            json=input_data,
            timeout=TASK1_TIMEOUT,
        )

        latency = (
            time.perf_counter()
            - start
        )

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Task 1 API could not be reached at {url}: {exc}"
        ) from exc

    if not response.ok:
        raise RuntimeError(
            f"Task 1 API returned HTTP "
            f"{response.status_code}: "
            f"{response.text[:1000]}"
        )

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "Task 1 API did not return valid JSON."
        ) from exc

    if not isinstance(result, dict):
        raise RuntimeError(
            "Task 1 API response must be a JSON object."
        )

    return result, latency