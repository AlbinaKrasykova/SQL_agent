"""
RAG: load PDFs/text from knowledge/, chunk, store in Chroma when available.
Falls back to simple keyword search if Chroma fails (e.g. Python 3.14 on Streamlit Cloud).
"""

from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
PDF_DIR = KNOWLEDGE_DIR / "pdfs"
CHROMA_DIR = Path(__file__).parent / "data" / "chroma"
COLLECTION_NAME = "health_nutrition"

CHUNK_SIZE = 600
CHUNK_OVERLAP = 80

_chroma_available: bool | None = None


def _chromadb_ready() -> bool:
    global _chroma_available
    if _chroma_available is not None:
        return _chroma_available
    try:
        import chromadb  # noqa: F401
        from chromadb.utils import embedding_functions  # noqa: F401

        _chroma_available = True
    except Exception:
        _chroma_available = False
    return _chroma_available


def _default_ef():
    from chromadb.utils import embedding_functions

    return embedding_functions.DefaultEmbeddingFunction()


def get_collection():
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_default_ef(),
    )


def _chunk_text(text: str) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP
    return chunks


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _gather_documents() -> list[tuple[str, str, str]]:
    docs: list[tuple[str, str, str]] = []
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    for path in sorted(PDF_DIR.glob("*.pdf")):
        try:
            text = _read_pdf(path)
        except Exception as e:
            print(f"Skip {path.name}: {e}")
            continue
        if text.strip():
            docs.append((path.stem, text, f"pdf:{path.name}"))

    for path in sorted(KNOWLEDGE_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if text.strip():
            docs.append((path.stem, text, f"txt:{path.name}"))

    return docs


def _load_all_chunks() -> list[dict]:
    chunks = []
    for doc_id, text, source in _gather_documents():
        for i, part in enumerate(_chunk_text(text)):
            chunks.append({"text": part, "source": source, "doc": doc_id, "id": f"{doc_id}_{i}"})
    return chunks


def _fallback_search(query: str, n_results: int = 4) -> list[dict]:
    """Keyword overlap search when Chroma is unavailable."""
    words = [w.lower() for w in query.split() if len(w) > 2]
    if not words:
        words = [query.lower()]

    scored = []
    for chunk in _load_all_chunks():
        text_lower = chunk["text"].lower()
        score = sum(1 for w in words if w in text_lower)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, chunk in scored[:n_results]:
        out.append(
            {
                "text": chunk["text"],
                "source": chunk["source"],
                "distance": 1.0 / (score + 1),
            }
        )
    if not out and scored == []:
        for chunk in _load_all_chunks()[:n_results]:
            out.append(
                {
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "distance": None,
                }
            )
    return out


def ingest(reset: bool = False) -> int:
    if not _chromadb_ready():
        print("Chroma not available; using file-based fallback search only.")
        return len(_load_all_chunks())

    import chromadb

    collection = get_collection()
    if reset:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        collection = get_collection()

    raw_docs = _gather_documents()
    if not raw_docs:
        print(f"No files found. Add PDFs to {PDF_DIR} or .txt to {KNOWLEDGE_DIR}")
        return 0

    ids, documents, metadatas = [], [], []
    for doc_id, text, source in raw_docs:
        for i, chunk in enumerate(_chunk_text(text)):
            ids.append(f"{doc_id}_{i}")
            documents.append(chunk)
            metadatas.append({"source": source, "doc": doc_id})

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    print(f"Indexed {len(raw_docs)} file(s), {len(ids)} chunk(s).")
    return len(ids)


def search(query: str, n_results: int = 4) -> list[dict]:
    if not _chromadb_ready():
        return _fallback_search(query, n_results)

    try:
        collection = get_collection()
        if collection.count() == 0:
            ingest()

        if collection.count() == 0:
            return _fallback_search(query, n_results)

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
        )
        out = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            out.append(
                {
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "distance": dist,
                }
            )
        return out
    except Exception as e:
        print(f"Chroma search failed ({e}); using fallback.")
        return _fallback_search(query, n_results)


if __name__ == "__main__":
    import sys

    reset = "--reset" in sys.argv
    ingest(reset=reset)
