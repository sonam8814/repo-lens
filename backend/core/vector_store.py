import hashlib
import os
from typing import Optional

import chromadb
from langchain_huggingface import HuggingFaceEmbeddings

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_data")

_embeddings: Optional[HuggingFaceEmbeddings] = None


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def get_chroma_client() -> chromadb.PersistentClient:
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


def _collection_name(session_id: str) -> str:
    """Derive a valid ChromaDB collection name from a session id."""
    slug = hashlib.md5(session_id.encode()).hexdigest()[:16]
    return f"repolens_{slug}"


def build_vector_store(session_id: str, chunks: list[dict]) -> str:
    """Embed code chunks and store them in a ChromaDB collection.

    Args:
        session_id: Unique identifier tying this collection to a user session.
        chunks: Output of parser.get_code_chunks() — each dict has
                "text" and "metadata" keys.

    Returns:
        The collection name that was created/updated.
    """
    if not chunks:
        raise ValueError("No code chunks to embed")

    embeddings = get_embeddings()
    client = get_chroma_client()
    col_name = _collection_name(session_id)

    existing = client.list_collections()
    if col_name in [str(c) for c in existing]:
        client.delete_collection(col_name)

    collection = client.get_or_create_collection(
        name=col_name,
        metadata={"hnsw:space": "cosine"},
    )

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [f"{session_id}_{i}" for i in range(len(chunks))]

    BATCH_SIZE = 256
    for start in range(0, len(texts), BATCH_SIZE):
        end = start + BATCH_SIZE
        batch_texts = texts[start:end]
        batch_ids = ids[start:end]
        batch_metadatas = metadatas[start:end]

        batch_embeddings = embeddings.embed_documents(batch_texts)

        collection.add(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=batch_embeddings,
            metadatas=batch_metadatas,
        )

    return col_name


def query_vector_store(
    session_id: str,
    query: str,
    n_results: int = 5,
) -> list[dict]:
    """Retrieve the most relevant code chunks for a natural-language query.

    Returns a list of dicts with keys: text, metadata, distance.
    """
    embeddings = get_embeddings()
    client = get_chroma_client()
    col_name = _collection_name(session_id)

    collection = client.get_collection(name=col_name)

    query_embedding = embeddings.embed_query(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    return [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]


def delete_collection(session_id: str) -> None:
    """Remove a session's vector store collection to free resources."""
    client = get_chroma_client()
    col_name = _collection_name(session_id)
    try:
        client.delete_collection(col_name)
    except ValueError:
        pass
