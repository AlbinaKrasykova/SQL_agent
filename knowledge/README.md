# Health knowledge for RAG

Drop PDFs here:

```
knowledge/pdfs/your-book.pdf
```

Or add `.txt` files in this folder (like `sample_hormones_nutrition.txt`).

Then index:

```bash
source ../.venv/bin/activate
python ingest_knowledge.py
```

The agent tool `search_health_knowledge` searches these chunks when you ask about nutrition, hormones, or general eating advice.
