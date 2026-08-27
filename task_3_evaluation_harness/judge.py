# evals/judge.py

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.prompts import (
    ChatPromptTemplate,
)
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


load_dotenv()


OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

OPENAI_LLM_MODEL = os.getenv(
    "OPENAI_LLM_MODEL"
)


if not OPENAI_API_KEY:
    raise EnvironmentError(
        "OPENAI_API_KEY is missing from .env"
    )

if not OPENAI_LLM_MODEL:
    raise EnvironmentError(
        "OPENAI_LLM_MODEL is missing from .env"
    )


class JudgeOutput(BaseModel):

    score: float = Field(
        ge=0.0,
        le=1.0,
    )

    passed: bool

    reasoning: str


JUDGE_SYSTEM_PROMPT = """
You are an expert evaluator of production AI systems.

You are evaluating ONE semantic quality criterion for an AI application's
output.

Do not rewrite the application output.
Do not improve it.
Do not assume facts that are not supplied.

The deterministic evaluator handles exact facts such as:
- account identity
- ticket IDs
- ticket windows
- metrics
- required structural fields
- exact evidence quotes

You should focus on SEMANTIC QUALITY:

Task 1:
- classification quality
- prioritisation reasoning
- routing relevance
- response usefulness
- handling ambiguity
- avoiding unsupported assumptions

Task 2:
- synthesis quality
- factual interpretation
- account-health reasoning
- meaningful risk interpretation
- TAM usefulness
- actionability
- avoiding unsupported claims

Scoring:

1.0 = clearly satisfies the criterion
0.75 = substantially satisfies it with a minor weakness
0.50 = partially satisfies it
0.25 = mostly fails but has limited useful content
0.0 = clearly fails or contradicts the criterion

Be conservative about hallucinations and contradictions.

The actual output should be judged against the supplied test input and,
where provided, the expected facts.
"""


class EvaluationJudge:

    def __init__(self) -> None:

        self.llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=OPENAI_LLM_MODEL,
            temperature=0.0,
        )

        self.structured_llm = (
            self.llm.with_structured_output(
                JudgeOutput
            )
        )

        self.prompt = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        JUDGE_SYSTEM_PROMPT,
                    ),
                    (
                        "human",
                        """
TASK:

{task}

TEST INPUT:

{test_input}

EXPECTED FACTS:

{expected_facts}

ACTUAL APPLICATION OUTPUT:

{actual_output}

CRITERION:

{criterion}

Provide only the structured evaluation result.
""",
                    ),
                ]
            )
        )

        self.chain = (
            self.prompt
            | self.structured_llm
        )

    def evaluate(
        self,
        task: str,
        test_input: dict[str, Any],
        expected_facts: Any,
        actual_output: Any,
        criterion: str,
    ) -> JudgeOutput:

        response = self.chain.invoke(
            {
                "task": task,
                "test_input": json.dumps(
                    test_input,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                "expected_facts": json.dumps(
                    expected_facts,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                "actual_output": json.dumps(
                    self._serialize_output(
                        actual_output
                    ),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                "criterion": criterion,
            }
        )

        return response

    @staticmethod
    def _serialize_output(
        output: Any,
    ) -> Any:

        if hasattr(
            output,
            "model_dump",
        ):
            return output.model_dump(
                mode="json"
            )

        return output