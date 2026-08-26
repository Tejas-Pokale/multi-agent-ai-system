from __future__ import annotations

import os
import re

from pathlib import Path

from typing import (
    Any,
    Literal,
    TypedDict,
    AsyncIterator,
)

from dotenv import load_dotenv

from langchain_chroma import Chroma

from langchain_community.retrievers import (
    BM25Retriever,
)

from langchain_core.documents import Document

from langchain_openai import (
    ChatOpenAI,
    OpenAIEmbeddings,
)

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from flashrank import (
    Ranker,
    RerankRequest,
)

from pydantic import BaseModel

from .schemas import (
    IssueCategory,
    KnowledgeBaseMatch,
    SimilarTicket,
    TicketInput,
    TriageResult,
    Urgency,
    TicketStatus,
)

from .prompts import (
    RETRIEVAL_ASSESSMENT_PROMPT,
    FINAL_TRIAGE_PROMPT,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY is not configured."
    )


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


CHROMA_PATH = (
    PROJECT_ROOT / "chroma_db"
)


# ============================================================
# CONFIGURATION
# ============================================================

TICKETS_COLLECTION = (
    "historical_tickets"
)

KNOWLEDGE_COLLECTION = (
    "knowledge_base"
)


MAX_HOPS = 3

DENSE_K = 10

BM25_K = 10

RETRIEVAL_K = 10

RERANK_TOP_K = 5

RRF_K = 60


# FlashRank relevance scores are NOT calibrated
# probabilities. We therefore use them for ranking,
# not as "percentage similarity".
MIN_RERANK_SCORE = 0.15


# ============================================================
# MODELS
# ============================================================

embeddings = OpenAIEmbeddings(
    model=os.environ.get(
        "OPENAI_EMBEDDING_MODEL"
    )
)


llm = ChatOpenAI(
    model=os.environ.get(
        "OPENAI_LLM_MODEL"
    ),
    temperature=0,
)


# ============================================================
# RERANKER
# ============================================================

reranker = Ranker(
    model_name="ms-marco-MiniLM-L-12-v2"
)


# ============================================================
# CHROMA
# ============================================================

tickets_vectorstore = Chroma(
    collection_name=TICKETS_COLLECTION,
    embedding_function=embeddings,
    persist_directory=str(
        CHROMA_PATH
    ),
)


knowledge_vectorstore = Chroma(
    collection_name=KNOWLEDGE_COLLECTION,
    embedding_function=embeddings,
    persist_directory=str(
        CHROMA_PATH
    ),
)


# ============================================================
# LOAD CHROMA DOCUMENTS
# ============================================================

def load_chroma_documents(
    vectorstore: Chroma,
) -> list[Document]:

    data = vectorstore.get(
        include=[
            "documents",
            "metadatas",
        ]
    )

    documents = []

    raw_documents = data.get(
        "documents",
        [],
    )

    raw_metadatas = data.get(
        "metadatas",
        [],
    )

    for index, text in enumerate(
        raw_documents
    ):

        if not text:
            continue

        metadata = {}

        if index < len(
            raw_metadatas
        ):

            metadata = (
                raw_metadatas[index]
                or {}
            )

        documents.append(
            Document(
                page_content=text,
                metadata=metadata,
            )
        )

    return documents


print(
    "Loading BM25 documents..."
)


ticket_documents = (
    load_chroma_documents(
        tickets_vectorstore
    )
)


knowledge_documents = (
    load_chroma_documents(
        knowledge_vectorstore
    )
)


print(
    f"Historical ticket documents: "
    f"{len(ticket_documents)}"
)


print(
    f"Knowledge-base documents: "
    f"{len(knowledge_documents)}"
)


# ============================================================
# BM25
# ============================================================

ticket_bm25 = None

if ticket_documents:

    ticket_bm25 = (
        BM25Retriever.from_documents(
            ticket_documents
        )
    )

    ticket_bm25.k = BM25_K


knowledge_bm25 = None

if knowledge_documents:

    knowledge_bm25 = (
        BM25Retriever.from_documents(
            knowledge_documents
        )
    )

    knowledge_bm25.k = BM25_K


# ============================================================
# STATE
# ============================================================

class AgentState(
    TypedDict,
    total=False,
):

    ticket: TicketInput

    hop: int

    ticket_query: str

    knowledge_query: str

    historical_results: list[dict]

    knowledge_results: list[dict]

    retrieval_sufficient: bool

    missing_information: list[str]

    refined_ticket_query: str

    refined_knowledge_query: str

    retrieval_target: list[str]

    final_result: TriageResult


# ============================================================
# RETRIEVAL ASSESSMENT
# ============================================================

class RetrievalAssessment(
    BaseModel
):

    sufficient: bool

    missing_information: list[str]

    refined_ticket_query: str

    refined_knowledge_query: str

    retrieval_target: list[
        Literal[
            "historical_tickets",
            "knowledge_base",
            "both",
        ]
    ]


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        text.lower(),
    ).strip()


# ============================================================
# EXTRACT ERROR SIGNATURES
# ============================================================

def extract_error_signatures(
    text: str,
) -> list[str]:

    patterns = [
        r"\b[A-Z][A-Z0-9_]+(?:_[A-Z0-9]+)+\b",

        r"\bERR[_A-Z0-9-]+\b",

        r"\b[A-Z]+_MISMATCH\b",

        r"\b[A-Z]+_TIMEOUT\b",

        r"\b[A-Z]+_UNAVAILABLE\b",
    ]

    found = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        for match in matches:

            value = match.strip()

            if value not in found:

                found.append(value)

    return found


# ============================================================
# IMPORTANT TERMS
# ============================================================

def extract_important_terms(
    ticket: TicketInput,
) -> list[str]:

    text = (
        f"{ticket.subject} "
        f"{ticket.body}"
    )

    errors = extract_error_signatures(
        text
    )

    terms = []

    if ticket.product:

        terms.append(
            ticket.product
        )

    terms.extend(
        errors
    )

    # Important technical terms.
    keywords = [
        "production",
        "connector",
        "connectors",
        "pipeline",
        "webhook",
        "authentication",
        "sso",
        "timeout",
        "connection",
        "permission",
        "permissions",
        "failed",
        "failure",
        "unreachable",
        "corrupted",
        "missing",
        "blocked",
    ]

    normalized = normalize_text(
        text
    )

    for keyword in keywords:

        if keyword in normalized:

            terms.append(
                keyword
            )

    # Remove duplicates.

    output = []

    for term in terms:

        if term and term not in output:

            output.append(term)

    return output


# ============================================================
# QUERY CONSTRUCTION
# ============================================================

def ticket_to_query(
    ticket: TicketInput,
) -> str:

    terms = extract_important_terms(
        ticket
    )

    return f"""
Subject:
{ticket.subject}

Body:
{ticket.body}

Product:
{ticket.product or "Unknown"}

Important technical terms:
{", ".join(terms)}
""".strip()


# ============================================================
# RERANKING TEXT
# ============================================================

def build_reranker_text(
    document: Document,
) -> str:

    metadata = (
        document.metadata
        or {}
    )

    metadata_parts = []

    preferred_fields = [
        "ticket_id",
        "product",
        "product_area",
        "category",
        "urgency",
        "status",
        "source",
        "section",
        "section_title",
        "file_path",
    ]

    for field in preferred_fields:

        value = metadata.get(
            field
        )

        if value:

            metadata_parts.append(
                f"{field}: {value}"
            )

    metadata_text = "\n".join(
        metadata_parts
    )

    return f"""
{metadata_text}

Document:
{document.page_content}
""".strip()


# ============================================================
# DOCUMENT KEY
# ============================================================

def document_key(
    document: Document,
) -> str:

    metadata = (
        document.metadata
        or {}
    )

    ticket_id = metadata.get(
        "ticket_id"
    )

    if ticket_id:

        return (
            f"ticket:{ticket_id}"
        )

    source = (
        metadata.get("source")
        or metadata.get("file_path")
        or ""
    )

    section = (
        metadata.get("section")
        or metadata.get(
            "section_title"
        )
        or ""
    )

    return (
        f"kb:{source}:{section}:"
        f"{document.page_content[:100]}"
    )


# ============================================================
# DENSE RETRIEVAL
# ============================================================

def dense_retrieve(
    vectorstore: Chroma,
    query: str,
) -> list[Document]:

    if not query.strip():

        return []

    try:

        return vectorstore.similarity_search(
            query,
            k=DENSE_K,
        )

    except Exception as exc:

        print(
            f"Dense retrieval error: {exc}"
        )

        return []


# ============================================================
# BM25
# ============================================================

def bm25_retrieve(
    retriever: BM25Retriever | None,
    query: str,
) -> list[Document]:

    if (
        retriever is None
        or not query.strip()
    ):

        return []

    try:

        retriever.k = BM25_K

        return retriever.invoke(
            query
        )

    except Exception as exc:

        print(
            f"BM25 retrieval error: {exc}"
        )

        return []


# ============================================================
# RRF
# ============================================================

def reciprocal_rank_fusion(
    dense_results: list[Document],
    bm25_results: list[Document],
) -> list[dict]:

    scores = {}

    documents = {}

    for rank, document in enumerate(
        dense_results,
        start=1,
    ):

        key = document_key(
            document
        )

        documents[key] = document

        scores[key] = (
            scores.get(
                key,
                0.0,
            )
            + 1.0
            / (
                RRF_K
                + rank
            )
        )

    for rank, document in enumerate(
        bm25_results,
        start=1,
    ):

        key = document_key(
            document
        )

        documents[key] = document

        scores[key] = (
            scores.get(
                key,
                0.0,
            )
            + 1.0
            / (
                RRF_K
                + rank
            )
        )

    ranked = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    results = []

    for key, score in ranked[
        :RETRIEVAL_K
    ]:

        results.append(
            {
                "document":
                    documents[key],

                "rrf_score":
                    score,
            }
        )

    return results


# ============================================================
# METADATA RELEVANCE
# ============================================================

def metadata_relevance(
    query: str,
    document: Document,
) -> float:

    metadata = (
        document.metadata
        or {}
    )

    query_normalized = normalize_text(
        query
    )

    score = 0.0

    # --------------------------------------------------------
    # Product
    # --------------------------------------------------------

    product = metadata.get(
        "product"
    )

    if product:

        if normalize_text(
            str(product)
        ) in query_normalized:

            score += 0.30


    # --------------------------------------------------------
    # Product area
    # --------------------------------------------------------

    product_area = metadata.get(
        "product_area"
    )

    if product_area:

        if normalize_text(
            str(product_area)
        ) in query_normalized:

            score += 0.20


    # --------------------------------------------------------
    # Error signatures
    # --------------------------------------------------------

    query_errors = (
        extract_error_signatures(
            query
        )
    )

    document_text = normalize_text(
        build_reranker_text(
            document
        )
    )

    for error in query_errors:

        if normalize_text(
            error
        ) in document_text:

            score += 0.25


    # --------------------------------------------------------
    # Exact important words
    # --------------------------------------------------------

    important_words = [
        "timeout",
        "connection",
        "pipeline",
        "production",
        "webhook",
        "authentication",
        "sso",
        "permission",
        "connector",
        "connectors",
    ]

    matches = 0

    for word in important_words:

        if (
            word in query_normalized
            and word in document_text
        ):

            matches += 1


    score += min(
        matches * 0.025,
        0.15,
    )


    return min(
        score,
        1.0,
    )


# ============================================================
# FLASHRANK
# ============================================================

def rerank_documents(
    query: str,
    candidates: list[dict],
) -> list[dict]:

    if not candidates:

        return []


    passages = []

    for index, candidate in enumerate(
        candidates
    ):

        document = (
            candidate["document"]
        )

        # IMPORTANT:
        #
        # Previously only page_content was sent
        # to FlashRank.
        #
        # Now metadata is explicitly included.

        passages.append(
            {
                "id": str(index),

                "text":
                    build_reranker_text(
                        document
                    ),

                "meta":
                    document.metadata
                    or {},
            }
        )


    try:

        request = RerankRequest(
            query=query,
            passages=passages,
        )

        ranked = reranker.rerank(
            request
        )

    except Exception as exc:

        print(
            f"Reranking failed: {exc}"
        )

        return []


    results = []

    for item in ranked:

        index = int(
            item["id"]
        )

        candidate = candidates[
            index
        ]

        document = candidate[
            "document"
        ]

        rerank_score = float(
            item["score"]
        )

        metadata_score = (
            metadata_relevance(
                query,
                document,
            )
        )

        # ----------------------------------------------------
        # Composite relevance
        #
        # FlashRank is strongest signal.
        # Metadata boosts exact product/error matches.
        # RRF provides hybrid retrieval evidence.
        # ----------------------------------------------------

        composite_score = (
            0.75 * rerank_score
            + 0.20 * metadata_score
            + 0.05 * min(
                candidate[
                    "rrf_score"
                ] * 10,
                1.0,
            )
        )

        results.append(
            {
                "document":
                    document,

                "rrf_score":
                    candidate[
                        "rrf_score"
                    ],

                "rerank_score":
                    rerank_score,

                "metadata_score":
                    metadata_score,

                "relevance_score":
                    composite_score,
            }
        )


    results.sort(
        key=lambda x:
            x["relevance_score"],
        reverse=True,
    )


    # --------------------------------------------------------
    # Keep top 5
    # --------------------------------------------------------

    results = results[
        :RERANK_TOP_K
    ]


    # --------------------------------------------------------
    # Remove very weak candidates
    # --------------------------------------------------------

    filtered = [
        result
        for result in results
        if result[
            "rerank_score"
        ] >= MIN_RERANK_SCORE
    ]


    return [
        {
            "content":
                result[
                    "document"
                ].page_content,

            "metadata":
                result[
                    "document"
                ].metadata
                or {},

            "rrf_score":
                result[
                    "rrf_score"
                ],

            "rerank_score":
                result[
                    "rerank_score"
                ],

            "metadata_score":
                result[
                    "metadata_score"
                ],

            "relevance_score":
                result[
                    "relevance_score"
                ],
        }
        for result in filtered
    ]


# ============================================================
# HYBRID RETRIEVAL
# ============================================================

def hybrid_retrieve_and_rerank(
    *,
    query: str,
    vectorstore: Chroma,
    bm25_retriever: BM25Retriever | None,
) -> list[dict]:

    dense_results = (
        dense_retrieve(
            vectorstore,
            query,
        )
    )

    bm25_results = (
        bm25_retrieve(
            bm25_retriever,
            query,
        )
    )

    fused_results = (
        reciprocal_rank_fusion(
            dense_results,
            bm25_results,
        )
    )

    return rerank_documents(
        query,
        fused_results,
    )


# ============================================================
# DEDUPLICATE
# ============================================================

def deduplicate_results(
    results: list[dict],
) -> list[dict]:

    seen = set()

    output = []

    for result in results:

        metadata = (
            result.get(
                "metadata",
                {},
            )
        )

        ticket_id = metadata.get(
            "ticket_id"
        )

        if ticket_id:

            key = (
                "ticket:"
                + str(ticket_id)
            )

        else:

            key = (
                str(
                    metadata.get(
                        "source"
                    )
                    or metadata.get(
                        "file_path"
                    )
                    or ""
                )
                + "|"
                + str(
                    metadata.get(
                        "section"
                    )
                    or metadata.get(
                        "section_title"
                    )
                    or ""
                )
                + "|"
                + result.get(
                    "content",
                    "",
                )[:100]
            )

        if key in seen:

            continue

        seen.add(key)

        output.append(
            result
        )

    return output


# ============================================================
# MERGE + RERANK ACROSS HOPS
# ============================================================

def merge_results(
    query: str,
    previous: list[dict],
    current: list[dict],
) -> list[dict]:

    merged = (
        deduplicate_results(
            previous + current
        )
    )

    if not merged:

        return []


    # --------------------------------------------------------
    # Convert back to candidate documents
    # --------------------------------------------------------

    candidates = []

    for item in merged:

        candidates.append(
            {
                "document":
                    Document(
                        page_content=
                            item[
                                "content"
                            ],

                        metadata=
                            item[
                                "metadata"
                            ],
                    ),

                "rrf_score":
                    item.get(
                        "rrf_score",
                        0.0,
                    ),
            }
        )


    # --------------------------------------------------------
    # Re-rank accumulated evidence
    # --------------------------------------------------------

    return rerank_documents(
        query,
        candidates,
    )


# ============================================================
# PREPARE TICKET
# ============================================================

def prepare_ticket(
    state: AgentState,
) -> AgentState:

    ticket = state[
        "ticket"
    ]

    query = ticket_to_query(
        ticket
    )

    print(
        "\nPreparing ticket..."
    )

    return {
        "hop": 1,

        "ticket_query":
            query,

        "knowledge_query":
            query,
    }


# ============================================================
# RETRIEVE
# ============================================================

def retrieve(
    state: AgentState,
) -> AgentState:

    hop = state.get(
        "hop",
        1,
    )

    ticket_query = state.get(
        "ticket_query",
        "",
    )

    knowledge_query = state.get(
        "knowledge_query",
        "",
    )

    print(
        f"\n{'=' * 60}"
    )

    print(
        f"RETRIEVAL HOP "
        f"{hop}/{MAX_HOPS}"
    )

    print(
        f"{'=' * 60}"
    )


    # --------------------------------------------------------
    # Historical tickets
    # --------------------------------------------------------

    print(
        "\nSearching historical tickets..."
    )

    current_historical = (
        hybrid_retrieve_and_rerank(
            query=ticket_query,

            vectorstore=
                tickets_vectorstore,

            bm25_retriever=
                ticket_bm25,
        )
    )


    # --------------------------------------------------------
    # Knowledge base
    # --------------------------------------------------------

    print(
        "Searching knowledge base..."
    )

    current_knowledge = (
        hybrid_retrieve_and_rerank(
            query=knowledge_query,

            vectorstore=
                knowledge_vectorstore,

            bm25_retriever=
                knowledge_bm25,
        )
    )


    # --------------------------------------------------------
    # Previous evidence
    # --------------------------------------------------------

    previous_historical = (
        state.get(
            "historical_results",
            [],
        )
    )

    previous_knowledge = (
        state.get(
            "knowledge_results",
            [],
        )
    )


    # --------------------------------------------------------
    # IMPORTANT:
    #
    # We do NOT simply append old top-5 to new top-5.
    #
    # We merge and rerank again.
    # --------------------------------------------------------

    historical_results = (
        merge_results(
            ticket_query,

            previous_historical,

            current_historical,
        )
    )

    knowledge_results = (
        merge_results(
            knowledge_query,

            previous_knowledge,

            current_knowledge,
        )
    )


    print(
        f"Historical results: "
        f"{len(historical_results)}"
    )

    print(
        f"Knowledge results: "
        f"{len(knowledge_results)}"
    )


    # --------------------------------------------------------
    # Debug ranking
    # --------------------------------------------------------

    print(
        "\nTop historical results:"
    )

    for index, item in enumerate(
        historical_results,
        start=1,
    ):

        metadata = item[
            "metadata"
        ]

        print(
            f"{index}. "
            f"{metadata.get('ticket_id')} | "
            f"{metadata.get('product')} | "
            f"{metadata.get('product_area')} | "
            f"rerank="
            f"{item.get('rerank_score'):.4f} | "
            f"metadata="
            f"{item.get('metadata_score'):.4f} | "
            f"final="
            f"{item.get('relevance_score'):.4f}"
        )


    print(
        "\nTop knowledge-base results:"
    )

    for index, item in enumerate(
        knowledge_results,
        start=1,
    ):

        metadata = item[
            "metadata"
        ]

        print(
            f"{index}. "
            f"{metadata.get('section') or metadata.get('section_title')} | "
            f"rerank="
            f"{item.get('rerank_score'):.4f} | "
            f"metadata="
            f"{item.get('metadata_score'):.4f} | "
            f"final="
            f"{item.get('relevance_score'):.4f}"
        )


    return {
        "historical_results":
            historical_results,

        "knowledge_results":
            knowledge_results,
    }


# ============================================================
# EVIDENCE CONTEXT
# ============================================================

def build_evidence_context(
    results: list[dict],
    max_chars: int = 3000,
) -> str:

    chunks = []

    for index, result in enumerate(
        results[:RERANK_TOP_K],
        start=1,
    ):

        metadata = (
            result.get(
                "metadata",
                {},
            )
        )

        chunks.append(
            f"""
--- Evidence {index} ---

Content:
{result.get("content", "")[:max_chars]}

Metadata:
{metadata}

Relevance score:
{result.get("relevance_score")}
""".strip()
        )

    return "\n\n".join(
        chunks
    )


# ============================================================
# ASSESS EVIDENCE
# ============================================================

def assess_evidence(
    state: AgentState,
) -> AgentState:

    ticket = state[
        "ticket"
    ]

    hop = state.get(
        "hop",
        1,
    )

    historical_context = (
        build_evidence_context(
            state.get(
                "historical_results",
                [],
            )
        )
        or "No relevant historical tickets found."
    )

    knowledge_context = (
        build_evidence_context(
            state.get(
                "knowledge_results",
                [],
            )
        )
        or "No relevant knowledge-base sections found."
    )


    prompt = (
        RETRIEVAL_ASSESSMENT_PROMPT.format(
            ticket_id=
                ticket.ticket_id,

            product=
                ticket.product,

            subject=
                ticket.subject,

            body=
                ticket.body,

            historical_context=
                historical_context,

            knowledge_context=
                knowledge_context,

            hop=
                hop,

            max_hops=
                MAX_HOPS,
        )
    )


    structured_llm = (
        llm.with_structured_output(
            RetrievalAssessment
        )
    )


    assessment = (
        structured_llm.invoke(
            prompt
        )
    )


    print(
        f"\nEvidence sufficient: "
        f"{assessment.sufficient}"
    )


    return {
        "retrieval_sufficient":
            assessment.sufficient,

        "missing_information":
            assessment.missing_information,

        "refined_ticket_query":
            assessment.refined_ticket_query,

        "refined_knowledge_query":
            assessment.refined_knowledge_query,

        "retrieval_target":
            assessment.retrieval_target,
    }


# ============================================================
# CONTINUE?
# ============================================================

def should_continue(
    state: AgentState,
) -> str:

    hop = state.get(
        "hop",
        1,
    )

    sufficient = state.get(
        "retrieval_sufficient",
        False,
    )


    if sufficient:

        return "reason"


    if hop >= MAX_HOPS:

        return "reason"


    return "refine"


# ============================================================
# REFINE QUERY
# ============================================================

def refine_query(
    state: AgentState,
) -> AgentState:

    next_hop = (
        state.get(
            "hop",
            1,
        )
        + 1
    )

    print(
        f"\nPreparing retrieval hop "
        f"{next_hop}/{MAX_HOPS}..."
    )


    return {
        "hop":
            next_hop,

        "ticket_query":
            state.get(
                "refined_ticket_query",
                state.get(
                    "ticket_query",
                    "",
                ),
            ),

        "knowledge_query":
            state.get(
                "refined_knowledge_query",
                state.get(
                    "knowledge_query",
                    "",
                ),
            ),
    }


# ============================================================
# FINAL REASONING
# ============================================================

def final_reasoning(
    state: AgentState,
) -> AgentState:

    ticket = state[
        "ticket"
    ]

    hop = state.get(
        "hop",
        1,
    )


    historical_results = (
        state.get(
            "historical_results",
            [],
        )
    )

    knowledge_results = (
        state.get(
            "knowledge_results",
            [],
        )
    )


    historical_context = (
        build_evidence_context(
            historical_results,
            max_chars=2500,
        )
        or
        "No relevant historical tickets found."
    )


    knowledge_context = (
        build_evidence_context(
            knowledge_results,
            max_chars=3000,
        )
        or
        "No relevant knowledge-base sections found."
    )


    prompt = (
        FINAL_TRIAGE_PROMPT.format(
            ticket_id=
                ticket.ticket_id,

            account_id=
                ticket.account_id,

            company=
                ticket.company,

            subject=
                ticket.subject,

            body=
                ticket.body,

            product=
                ticket.product,

            plan=
                ticket.plan_tier,

            channel=
                ticket.channel,

            tags=
                ticket.tags,

            historical_context=
                historical_context,

            knowledge_context=
                knowledge_context,

            hop=
                hop,
        )
    )


    print(
        "\nRunning final triage reasoning..."
    )


    structured_llm = (
        llm.with_structured_output(
            TriageResult
        )
    )


    result = (
        structured_llm.invoke(
            prompt
        )
    )


    # ========================================================
    # HISTORICAL TICKETS
    # ========================================================

    similar_tickets = []


    for item in historical_results[
        :RERANK_TOP_K
    ]:

        metadata = (
            item.get(
                "metadata",
                {},
            )
        )


        ticket_id = metadata.get(
            "ticket_id"
        )


        if not ticket_id:

            continue


        category = metadata.get(
            "category"
        )

        urgency = metadata.get(
            "urgency"
        )

        status = metadata.get(
            "status"
        )


        try:

            parsed_category = (
                IssueCategory(
                    category
                )
                if category
                else None
            )

        except ValueError:

            parsed_category = None


        try:

            parsed_urgency = (
                Urgency(
                    urgency
                )
                if urgency
                else None
            )

        except ValueError:

            parsed_urgency = None


        try:

            parsed_status = (
                TicketStatus(
                    status
                )
                if status
                else None
            )

        except ValueError:

            parsed_status = None


        similar_tickets.append(
            SimilarTicket(
                ticket_id=str(
                    ticket_id
                ),

                similarity_score=float(
                    item.get(
                        "relevance_score",
                        0.0,
                    )
                ),

                product=metadata.get(
                    "product"
                ),

                product_area=metadata.get(
                    "product_area"
                ),

                category=parsed_category,

                urgency=parsed_urgency,

                status=parsed_status,
            )
        )


    # ========================================================
    # KNOWLEDGE BASE
    # ========================================================

    kb_match = None


    # IMPORTANT:
    #
    # Do not allow the LLM's boolean alone to determine
    # whether a document exists.
    #
    # We select the actual top retrieved document
    # deterministically.

    if (
        result.known_issue
        and knowledge_results
    ):

        best = knowledge_results[
            0
        ]

        metadata = (
            best.get(
                "metadata",
                {},
            )
        )


        kb_match = (
            KnowledgeBaseMatch(
                source=(
                    metadata.get(
                        "source"
                    )
                    or
                    metadata.get(
                        "file_path"
                    )
                    or
                    "unknown"
                ),

                section=(
                    metadata.get(
                        "section"
                    )
                    or
                    metadata.get(
                        "section_title"
                    )
                ),

                category=metadata.get(
                    "category"
                ),

                product=metadata.get(
                    "product"
                ),

                relevance_score=float(
                    best.get(
                        "relevance_score",
                        0.0,
                    )
                ),

                excerpt=best.get(
                    "content",
                    "",
                )[:1000],
            )
        )


    # ========================================================
    # DETERMINISTIC EVIDENCE
    # ========================================================

    result = result.model_copy(
        update={
            "similar_tickets":
                similar_tickets,

            "knowledge_base_match":
                kb_match,
        }
    )


    return {
        "final_result":
            result
    }


# ============================================================
# LANGGRAPH
# ============================================================

def build_graph():

    graph = StateGraph(
        AgentState
    )


    graph.add_node(
        "prepare_ticket",
        prepare_ticket,
    )

    graph.add_node(
        "retrieve",
        retrieve,
    )

    graph.add_node(
        "assess_evidence",
        assess_evidence,
    )

    graph.add_node(
        "refine_query",
        refine_query,
    )

    graph.add_node(
        "final_reasoning",
        final_reasoning,
    )


    graph.add_edge(
        START,
        "prepare_ticket",
    )

    graph.add_edge(
        "prepare_ticket",
        "retrieve",
    )

    graph.add_edge(
        "retrieve",
        "assess_evidence",
    )


    graph.add_conditional_edges(
        "assess_evidence",

        should_continue,

        {
            "refine":
                "refine_query",

            "reason":
                "final_reasoning",
        },
    )


    graph.add_edge(
        "refine_query",
        "retrieve",
    )

    graph.add_edge(
        "final_reasoning",
        END,
    )


    return graph.compile()


# ============================================================
# COMPILED AGENT
# ============================================================

triage_agent = (
    build_graph()
)


# ============================================================
# NORMAL PYTHON API
# ============================================================

def triage_ticket(
    ticket: TicketInput,
) -> TriageResult:

    result = (
        triage_agent.invoke(
            {
                "ticket":
                    ticket,
            }
        )
    )

    return result[
        "final_result"
    ]


# ============================================================
# STREAMING API
# ============================================================

async def triage_ticket_stream(
    ticket: TicketInput,
) -> AsyncIterator[dict]:
    """
    Stream LangGraph execution events.

    Emits:
        start
        progress
        node_complete
        result       <-- exactly once
        done
        error
    """

    # ========================================================
    # STATE
    # ========================================================

    final_result = None

    result_emitted = False

    completed_nodes = set()


    yield {
        "event": "start",
        "message": "Ticket triage started.",
    }


    try:

        # ====================================================
        # LANGGRAPH EVENT STREAM
        # ====================================================

        async for event in triage_agent.astream_events(
            {
                "ticket": ticket,
            },
            version="v2",
        ):

            event_name = event.get(
                "event"
            )

            metadata = event.get(
                "metadata",
                {},
            ) or {}

            node_name = metadata.get(
                "langgraph_node"
            )


            # =================================================
            # NODE START
            # =================================================

            if (
                event_name == "on_chain_start"
                and node_name
            ):

                messages = {

                    "prepare_ticket":
                        "Preparing ticket for retrieval...",

                    "retrieve":
                        "Running hybrid retrieval...",

                    "assess_evidence":
                        "Evaluating retrieved evidence...",

                    "refine_query":
                        "Evidence is incomplete. Refining the retrieval query...",

                    "final_reasoning":
                        "Generating final triage...",
                }


                message = messages.get(
                    node_name,
                    f"Running {node_name}...",
                )


                yield {
                    "event": "progress",

                    "node": node_name,

                    "message": message,
                }


            # =================================================
            # NODE END
            # =================================================

            elif (
                event_name == "on_chain_end"
                and node_name
            ):

                event_data = event.get(
                    "data",
                     {},
                )  or {}

                output = event_data.get(
                    "output"
                )


                # ---------------------------------------------
                # Capture final result
                # ---------------------------------------------

                if (
                    node_name == "final_reasoning"
                   and output is not None
                ):

                    final_result = output


                # ---------------------------------------------
                # Don't duplicate node completion
                # ---------------------------------------------

                if node_name not in completed_nodes:

                    completed_nodes.add(
                        node_name
                    )

                    yield {
                        "event": "node_complete",

                      "node": node_name,

                        "message":
                            f"{node_name} completed.",
                    }

        # ====================================================
        # GRAPH COMPLETED
        # ====================================================

        if final_result is None:

            raise RuntimeError(
                "LangGraph completed but "
                "final_reasoning did not produce "
                "a final result."
            )


        # ====================================================
        # NORMALIZE FINAL RESULT
        # ====================================================

        if isinstance(
            final_result,
            TriageResult,
        ):

            result_data = final_result.model_dump(
                mode="json"
            )

        elif isinstance(
            final_result,
            dict,
        ):

            result_data = final_result

        else:

            # -----------------------------------------------
            # Defensive fallback
            # -----------------------------------------------

            try:

                result_data = (
                    final_result.model_dump(
                        mode="json"
                    )
                )

            except AttributeError:

                raise RuntimeError(
                    "Unexpected final result type: "
                    f"{type(final_result).__name__}"
                )


        # ====================================================
        # EMIT RESULT EXACTLY ONCE
        # ====================================================

        if not result_emitted:

            result_emitted = True

            yield {
                "event": "result",

                "data": result_data,
            }


        # ====================================================
        # DONE
        # ====================================================

        yield {
            "event": "done",

            "message":
                "Ticket triage completed.",
        }


    except Exception as exc:

        # ====================================================
        # ERROR
        # ====================================================

        yield {
            "event": "error",

            "message":
                f"Triage failed: {exc}",
        }