# Getting Started

## Project Structure

```
/
├── README.md                          # Main documentation
├── approach.md                        # Detailed methodology
├── getting_started.md                 # This file
├── app/                               # Full-stack evaluation application
│   ├── README.md                      # App-specific documentation
│   ├── AGENTS.md                      # Development session history
│   ├── backend/                       # FastAPI server
│   │   ├── main.py                    # API entry point
│   │   ├── models.py                  # SQLAlchemy database models
│   │   ├── schemas.py                 # Pydantic request/response schemas
│   │   ├── routers/                   # API endpoints
│   │   │   ├── transcripts.py
│   │   │   ├── experiments.py
│   │   │   ├── judges.py
│   │   │   └── evaluations.py
│   │   └── services/                  # Business logic
│   │       ├── llm_service.py         # OpenAI API calls
│   │       ├── evaluation_service.py  # Evaluation orchestration
│   │       ├── judge_service.py       # Dual-pass judging logic
│   │       ├── metrics_service.py     # Precision/recall/F1 calculation
│   │       ├── ground_truth_service.py
│   │       └── schema_utils.py        # JSON schema analysis
│   └── frontend/                      # Next.js web interface
│       ├── app/                       # Pages (Next.js App Router)
│       ├── components/                # React components
│       └── lib/                       # API client and utilities
├── preparation/                       # Transcript generation pipeline
│   ├── README.md                      # Detailed generation guide
│   ├── run.py                         # Schema validation tool
│   ├── generate_transcript_prompts.py # Stage 2: Create prompts
│   ├── generate_transcripts.py       # Stage 3: Generate transcripts
│   ├── start/                         # Template transcripts and schemas
│   └── prompts/                       # Generated prompts (34 personas)
└── transcripts/                       # Generated synthetic transcripts (40)
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key

## Quick Start

### 1. Generate Transcripts (Optional - 40 already included)

```bash
cd preparation
pip install -r requirements.txt
export OPENAI_API_KEY='your-key'
python generate_transcripts.py --max 5
```

### 2. Run Backend

```bash
cd app/backend
pip install -r requirements.txt
cp .env.example .env  # Add your OPENAI_API_KEY
python main.py
```

The API will be available at http://localhost:8000
- API docs: http://localhost:8000/docs

### 3. Run Frontend

```bash
cd app/frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:3000

## Basic Workflow

1. **View Transcripts** - Browse generated conversations
2. **Create a Judge** - Define matching rules and entity types
3. **Create an Experiment** - Specify extraction prompt and JSON schema
4. **Run Evaluation** - Judge evaluates experiment on all transcripts
5. **View Results** - Leaderboard with precision/recall/F1, detailed per-transcript breakdowns

See [app/README.md](app/README.md) for detailed usage instructions.

## Technology Stack

### Backend
- FastAPI (async Python web framework)
- SQLAlchemy (async ORM)
- SQLite (database)
- OpenAI Python SDK
- Pydantic (data validation)

### Frontend
- Next.js 15 (React framework with App Router)
- TypeScript
- shadcn/ui (component library)
- TailwindCSS
- React Query (server state management)
- Monaco Editor (JSON editing)

### Transcript Generation
- OpenAI GPT-5.1 (temperature=1.0 for diversity)

### Evaluation
- OpenAI GPT-4o/GPT-5 (temperature=0.0 for reproducibility)
- Multiprocessing (parallel transcript evaluation)

