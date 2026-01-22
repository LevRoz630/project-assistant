"""Vector store operations using ChromaDB."""

import contextlib
from pathlib import Path

from config import get_settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

settings = get_settings()


def get_embeddings():
    """Get the embeddings model."""
    return OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        model="text-embedding-3-small",
    )


def get_vector_store() -> Chroma:
    """Get or create the ChromaDB vector store."""
    # Ensure directory exists
    Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)

    return Chroma(
        collection_name="personal_notes",
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_directory,
    )


def get_text_splitter():
    """Get the text splitter for chunking documents."""
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


async def ingest_document(
    content: str,
    source_path: str,
    metadata: dict | None = None,
) -> int:
    """Ingest a document into the vector store."""
    vector_store = get_vector_store()
    splitter = get_text_splitter()

    # Create document with metadata
    doc_metadata = {
        "source": source_path,
        "type": "note",
    }
    if metadata:
        doc_metadata.update(metadata)

    # Split into chunks
    chunks = splitter.split_text(content)

    # Create Document objects
    documents = [
        Document(
            page_content=chunk,
            metadata={**doc_metadata, "chunk_index": i},
        )
        for i, chunk in enumerate(chunks)
    ]

    # Delete existing documents with same source
    with contextlib.suppress(Exception):
        existing = vector_store.get(where={"source": source_path})
        if existing and existing.get("ids"):
            vector_store.delete(ids=existing["ids"])

    # Add new documents
    if documents:
        vector_store.add_documents(documents)

    return len(documents)


async def delete_document(source_path: str) -> bool:
    """Delete a document from the vector store."""
    vector_store = get_vector_store()

    with contextlib.suppress(Exception):
        existing = vector_store.get(where={"source": source_path})
        if existing and existing.get("ids"):
            vector_store.delete(ids=existing["ids"])
            return True

    return False


async def search_documents(
    query: str,
    k: int = 5,
    filter_metadata: dict | None = None,
) -> list[dict]:
    """Search for relevant documents."""
    vector_store = get_vector_store()

    # Perform similarity search
    results = vector_store.similarity_search_with_score(
        query=query,
        k=k,
        filter=filter_metadata,
    )

    # Format results
    formatted = []
    for doc, score in results:
        formatted.append(
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "metadata": doc.metadata,
                "score": score,
            }
        )

    return formatted


async def get_context_for_query(query: str, k: int = 5) -> str:
    """Get formatted context string for a query."""
    results = await search_documents(query, k=k)

    if not results:
        return ""

    context_parts = []
    for result in results:
        source = result["source"]
        content = result["content"]
        context_parts.append(f"[From: {source}]\n{content}")

    return "\n\n---\n\n".join(context_parts)


async def get_collection_stats() -> dict:
    """Get statistics about the vector store collection."""
    vector_store = get_vector_store()

    try:
        collection = vector_store._collection
        count = collection.count()

        return {
            "total_chunks": count,
            "persist_directory": settings.chroma_persist_directory,
        }
    except Exception as e:
        return {
            "error": str(e),
            "total_chunks": 0,
        }
