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

## Test

```bash
uv run pytest
```

Fallback:

```bash
.\.venv\Scripts\python -m pytest
```

