# Yu AI Agent Python

Python FastAPI version of the Yu AI Agent backend.

## Setup

Recommended with `uv`:

```bash
uv sync --extra dev
```

Fallback with standard Python tooling:

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## Run

```bash
uv run uvicorn app.main:app --reload --port 8124
```

Fallback:

```bash
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8124
```

## Configure LLM

Create `.env` from `.env.example` and fill your provider settings. DeepSeek example:

```env
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=your-deepseek-api-key
LLM_MODEL=deepseek-chat
```

Call the chat endpoint:

```bash
curl -X POST http://localhost:8124/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"你好，请用一句话介绍你自己\",\"chat_id\":\"demo\"}"
```

## Test

```bash
uv run pytest
```

Fallback:

```bash
.\.venv\Scripts\python -m pytest
```
