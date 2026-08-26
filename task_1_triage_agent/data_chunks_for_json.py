import json
from langchain_core.documents import Document


def chunk_tickets(path: str) -> list[Document]:

    # ---------------------------------------------------------
    # Load JSON
    # ---------------------------------------------------------
    with open(path, "r", encoding="utf-8") as file:
        tickets = json.load(file)

    documents = []

    # ---------------------------------------------------------
    # One ticket = one document
    # ---------------------------------------------------------
    for ticket in tickets:

        subject = ticket.get("subject", "").strip()
        body = ticket.get("body", "").strip()

        # Text that will be embedded
        page_content = f"""Subject: {subject}

Body:
{body}""".strip()

        # Everything useful for filtering / retrieval
        metadata = {
            "document_type": "historical_ticket",

            "ticket_id": ticket.get("ticket_id"),
            "account_id": ticket.get("account_id"),
            "company": ticket.get("company"),

            "product": ticket.get("product"),
            "product_area": ticket.get("product_area"),
            "category": ticket.get("category"),
            "urgency": ticket.get("urgency"),

            "status": ticket.get("status"),
            "plan_tier": ticket.get("plan_tier"),

            "assigned_agent": ticket.get("assigned_agent"),

            "created_at": ticket.get("created_at"),
            "updated_at": ticket.get("updated_at"),

            "channel": ticket.get("channel"),
            "satisfaction_score": ticket.get("satisfaction_score"),

            # Chroma metadata should contain simple values,
            # so convert the list to a string.
            "tags": ", ".join(ticket.get("tags", [])),
        }

        documents.append(
            Document(
                page_content=page_content,
                metadata=metadata
            )
        )

    return documents


# -------------------------------------------------------------
# Example
# -------------------------------------------------------------

# docs = chunk_tickets(r"data/tickets.json")

# print(f"Total documents: {len(docs)}")

# for doc in docs[:3]:

#     print("\n" + "=" * 80)

#     print("PAGE CONTENT:")
#     print(doc.page_content)

#     print("\nMETADATA:")
#     print(doc.metadata)