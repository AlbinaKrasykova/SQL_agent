"""Index PDFs and text files into the local vector database."""

from rag import ingest

if __name__ == "__main__":
    import sys

    ingest(reset="--reset" in sys.argv)
