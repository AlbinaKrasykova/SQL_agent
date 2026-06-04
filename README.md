# SQL_agent

Natural-language questions over your `health_logs` SQLite database, using a local Ollama model to generate SQL.

## Setup

1. Install and run [Ollama](https://ollama.com), then pull a model:

   ```bash
   ollama pull qwen2.5
   ```

2. Create a virtual environment and install dependencies (macOS Homebrew Python requires this):

   ```bash
   cd "/path/to/SQL_agent"
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create sample data (if you have not already):

   ```bash
   python setup_health_db.py
   ```

## Run the agent

```bash
source .venv/bin/activate
python lama_agent.py
```

Example: `What is the average heart rate?`

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'ollama'` | Activate `.venv` and run `pip install -r requirements.txt` |
| `model 'qwen2.5' not found` | Run `ollama pull qwen2.5` or change `MODEL` in `lama_agent.py` to match `ollama list` |
| Connection errors to Ollama | Start the Ollama app or run `ollama serve` |
