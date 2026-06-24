# SentinelAI Backend

FastAPI backend for the SentinelAI VAPT platform.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env  # fill in values
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Health check

```bash
curl http://localhost:8000/api/v1/health
```
