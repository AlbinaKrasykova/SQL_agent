"""
RAG: load PDFs/text from knowledge/, chunk, store in local Chroma vector DB.
"""

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
PDF_DIR = KNOWLEDGE_DIR / "pdfs"
CHROMA_DIR = Path(__file__).parent / "data" / "chroma"
COLLECTION_NAME = "health_nutrition"

CHUNK_SIZE = 600
CHUNK_OVERLAP = 80


def _default_ef():
    return embedding_functions.DefaultEmbeddingFunction()


def get_collection():
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
    """Returns list of (doc_id, text, source_label)."""
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


def ingest(reset: bool = False) -> int:
    """Index all PDFs in knowledge/pdfs/ and .txt in knowledge/. Returns chunk count."""
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
    """Return top chunks: text, source, distance."""
    collection = get_collection()
    if collection.count() == 0:
        ingest()

    if collection.count() == 0:
        return []

    results = collection.query(query_texts=[query], n_results=min(n_results, collection.count()))
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


if __name__ == "__main__":
    import sys

    reset = "--reset" in sys.argv
    ingest(reset=reset)
