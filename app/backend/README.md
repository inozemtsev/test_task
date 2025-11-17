# Transcript Analysis Backend

FastAPI backend for the Transcript Analysis & LLM Evaluation app.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```bash
cp .env.example .env
```

4. Add your OpenAI API key to the `.env` file:
```
OPENAI_API_KEY=sk-your-api-key-here
```

## Running the Server

```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Features

- Transcript management (CRUD operations)
- LLM Judge configuration with characteristics
- Experiment creation (prompt + schema + model)
- Evaluation runner with real-time progress
- Leaderboard for experiments

## API Endpoints

See `/docs` for full API documentation.
