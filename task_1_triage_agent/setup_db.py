import os
from pathlib import Path

from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from task_1_triage_agent.data_chunks_for_json import chunk_tickets
from task_1_triage_agent.data_chunks_for_md import getDocs


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

TICKETS_PATH = Path("data/tickets.json")

KNOWLEDGE_BASE_PATH = Path("knowledge-base")

CHROMA_PATH =  "chroma_db"

TICKETS_COLLECTION = "historical_tickets"

KNOWLEDGE_COLLECTION = "knowledge_base"

EMBEDDING_MODEL = "text-embedding-3-small"


# ============================================================
# VALIDATE OPENAI API KEY
# ============================================================

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY is not configured."
    )


# ============================================================
# EMBEDDINGS
# ============================================================

embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL
)


# ============================================================
# LOAD HISTORICAL TICKETS
# ============================================================

def load_tickets():

    print("\nLoading historical tickets...")

    if not TICKETS_PATH.exists():
        raise FileNotFoundError(
            f"tickets.json not found:\n{TICKETS_PATH}"
        )

    documents = chunk_tickets(
        str(TICKETS_PATH)
    )

    print(
        f"Loaded {len(documents)} ticket documents."
    )

    return documents


# ============================================================
# LOAD KNOWLEDGE BASE
# ============================================================

def load_knowledge_base():

    print("\nLoading knowledge base...")

    if not KNOWLEDGE_BASE_PATH.exists():
        raise FileNotFoundError(
            f"Knowledge base not found:\n"
            f"{KNOWLEDGE_BASE_PATH}"
        )

    documents = []

    # --------------------------------------------------------
    # Find every .md file recursively
    #
    # billing/
    # onboarding/
    # products/
    # troubleshooting/
    # --------------------------------------------------------

    markdown_files = sorted(
        KNOWLEDGE_BASE_PATH.rglob("*.md")
    )

    print(
        f"Found {len(markdown_files)} Markdown files."
    )

    for file_path in markdown_files:

        print(
            f"  Processing: "
            f"{file_path.relative_to(KNOWLEDGE_BASE_PATH)}"
        )

        file_documents = getDocs(
            str(file_path)
        )

        documents.extend(file_documents)

    print(
        f"Loaded {len(documents)} "
        f"knowledge-base documents."
    )

    return documents


# ============================================================
# CREATE / RECREATE CHROMA COLLECTION
# ============================================================

def create_collection(
    collection_name,
    documents,
):
    """
    Creates a fresh Chroma collection and inserts documents.

    The collection is recreated each time setup_db.py runs,
    so running this script after changing source data will
    rebuild the collection.
    """

    print(
        f"\nCreating collection: "
        f"{collection_name}"
    )

    # --------------------------------------------------------
    # Create initial Chroma instance
    # --------------------------------------------------------

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_PATH),
    )

    # --------------------------------------------------------
    # Delete existing collection
    # --------------------------------------------------------

    try:

        vectorstore.delete_collection()

        print(
            f"Deleted existing collection: "
            f"{collection_name}"
        )

    except Exception:

        # Collection may not exist yet
        pass

    # --------------------------------------------------------
    # Create fresh collection
    # --------------------------------------------------------

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_PATH),
    )

    # --------------------------------------------------------
    # Insert documents
    # --------------------------------------------------------

    if documents:

        vectorstore.add_documents(
            documents
        )

    print(
        f"Inserted {len(documents)} documents "
        f"into '{collection_name}'."
    )

    return vectorstore


# ============================================================
# SETUP DATABASE
# ============================================================

def setup_database():

    print("=" * 70)
    print("SETTING UP CHROMA DATABASE")
    print("=" * 70)

    print(
        f"\nChroma path:\n"
        f"{CHROMA_PATH}"
    )

    # --------------------------------------------------------
    # Load data using EXISTING chunking implementations
    # --------------------------------------------------------

    ticket_documents = load_tickets()

    knowledge_documents = load_knowledge_base()

    # --------------------------------------------------------
    # Create historical ticket collection
    # --------------------------------------------------------

    create_collection(
        collection_name=TICKETS_COLLECTION,
        documents=ticket_documents,
    )

    # --------------------------------------------------------
    # Create knowledge-base collection
    # --------------------------------------------------------

    create_collection(
        collection_name=KNOWLEDGE_COLLECTION,
        documents=knowledge_documents,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("CHROMA DATABASE SETUP COMPLETE")
    print("=" * 70)

    print(
        f"\nDatabase:"
        f"\n  {CHROMA_PATH}"
    )

    print(
        f"\nCollections:"
        f"\n  1. {TICKETS_COLLECTION}"
        f"\n  2. {KNOWLEDGE_COLLECTION}"
    )

    print(
        f"\nHistorical tickets:"
        f"\n  {len(ticket_documents)}"
    )

    print(
        f"\nKnowledge-base sections:"
        f"\n  {len(knowledge_documents)}"
    )

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    setup_database()