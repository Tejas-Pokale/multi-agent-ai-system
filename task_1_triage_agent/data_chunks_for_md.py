import os
import re

from langchain_core.documents import Document


def getDocs(path: str) -> list[Document]:

    # =========================================================
    # 1. Read markdown file
    # =========================================================

    with open(path, "r", encoding="utf-8") as file:
        data = file.read()

    # =========================================================
    # 2. File-level metadata
    # =========================================================

    file_name = os.path.basename(path)

    file_stem = os.path.splitext(file_name)[0]

    # Parent directory becomes category
    #
    # knowledge-base/
    #     billing/
    #         billing-and-plans.md
    #
    # category = billing
    category = os.path.basename(
        os.path.dirname(path)
    )

    # =========================================================
    # 3. Split document on ---
    #
    # Supports:
    #
    # ---
    #
    # **---
    # =========================================================

    sections = re.split(
        r"\n\s*\*{0,2}---\*{0,2}\s*\n",
        data
    )

    documents = []

    # =========================================================
    # 4. Process every section
    # =========================================================

    section_index = 0

    for section in sections:

        section = section.strip()

        # Skip empty sections
        if not section:
            continue

        section_index += 1

        # =====================================================
        # 5. Find first Markdown heading
        #
        # Supports:
        #
        # # Title
        # ## Title
        # ### Title
        #
        # Also supports your format:
        #
        # **# Title**
        # **## Title**
        # =====================================================

        heading_match = re.search(
            r"^\s*\*{0,2}(#{1,6})\s+(.+?)\*{0,2}\s*$",
            section,
            re.MULTILINE
        )

        if heading_match:

            heading_marker = heading_match.group(1)

            section_title = heading_match.group(2).strip()

            # Remove bold markdown
            section_title = section_title.replace(
                "**",
                ""
            ).strip()

            # # = 1
            # ## = 2
            # ### = 3
            section_level = len(heading_marker)

        else:

            section_title = "Untitled"

            section_level = 0

        # =====================================================
        # 6. Create rich metadata
        # =====================================================

        metadata = {

            # File information
            "source": file_name,
            "file_path": path,
            "document_id": file_stem,

            # Document classification
            "document_type": "reference_guide",
            "category": category,

            # Section information
            "section": section_title,
            "section_level": section_level,
            "section_index": section_index,

            # Future RAG/chunking fields
            "parent_section": None,
            "chunk_index": 0,

            # Versioning
            "version": "1",
        }

        # =====================================================
        # 7. Create LangChain Document
        # =====================================================

        document = Document(
            page_content=section,
            metadata=metadata
        )

        documents.append(document)

    # =========================================================
    # 8. Return documents
    # =========================================================

    return documents


# =============================================================
# TEST
# =============================================================

docs = getDocs(
    r"knowledge-base/products/cloudsync.md"
)


# =============================================================
# Display results
# =============================================================

# print(f"Total documents: {len(docs)}")

# print("=" * 100)

# for i, doc in enumerate(docs, start=1):

#     print(f"\nDOCUMENT {i}")

#     print("\nMETADATA:")
#     for key, value in doc.metadata.items():
#         print(f"  {key}: {value}")

#     print("\nCONTENT:")
#     print(doc.page_content)

#     print("=" * 100)