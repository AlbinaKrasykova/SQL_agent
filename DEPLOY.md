# Share a public link (Streamlit Community Cloud)

Anyone can open your app in a browser **without installing Python**.  
The hosted app runs in **demo mode** (no Ollama on Streamlit servers). Logging, charts, RAG snippets, and rule-based answers still work.

Full AI agent with Ollama = run on your Mac (`streamlit run app.py`).

---

## Step 1 — Push code to GitHub

```bash
cd "/Users/albinakrasykova/Desktop/new projects/SQL_agent"
git init   # if not already
git add app.py agent.py schema.py db.py tools.py rag.py demo_agent.py deploy_utils.py
git add lama_agent.py ingest_knowledge.py requirements.txt README.md DEPLOY.md
git add knowledge/ assets/ .streamlit/
git add .gitignore
git commit -m "Health diary app for Streamlit Cloud"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/SQL_agent.git
git push -u origin main
```

Do **not** commit `health.db`, `.venv/`, or `data/chroma/` (listed in `.gitignore`).

---

## Step 2 — Deploy on Streamlit Cloud

1. Go to [https://share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. **New app** → pick your repo `SQL_agent`
4. **Main file path:** `app.py`
5. **Branch:** `main`
6. Click **Deploy**

First boot may take a few minutes (installs `chromadb`, indexes sample knowledge).

---

## Step 3 — Share the link

You get a URL like:

```text
https://your-app-name.streamlit.app
```

Send that link to anyone. They can:

- View Overview charts (demo mood/food + wearable)
- Log mood and meals (stored in the app’s temporary cloud DB)
- Use **Ask agent** in demo mode

---

## What works on the public link vs locally

| Feature | Public link (Cloud) | Your Mac |
|---------|---------------------|----------|
| Log mood / food | Yes | Yes |
| Charts | Yes (demo seed data) | Yes (your data) |
| RAG knowledge search | Yes | Yes |
| Full Ollama agent loop | No (demo agent) | Yes |

---

## Troubleshooting deploy

| Issue | Fix |
|-------|-----|
| Build fails on `chromadb` | Check `requirements.txt` is in repo root |
| App crashes on start | View logs on share.streamlit.io → Manage app |
| Empty knowledge answers | Wait for first deploy to finish; sample `.txt` is in `knowledge/` |
| Want real AI online | Use a VPS with Ollama (see README) |

---

## Update the live app

```bash
git add .
git commit -m "Update app"
git push
```

Streamlit Cloud redeploys automatically.
