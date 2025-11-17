# Transcript Analysis & LLM Evaluation App

A full-stack application for analyzing financial advisor fact-find transcripts and evaluating LLM extraction quality using configurable judges.

## Features

### 1. Transcript Management
- View all transcripts from the `/transcripts` folder
- Add new transcripts manually via the UI
- View transcripts individually
- Compare two transcripts side-by-side
- Delete manually added transcripts

### 2. LLM Judge Configuration
- Create judges with specific LLM models
- Define characteristics (boolean evaluation criteria) for each judge
- Each characteristic has a custom prompt for evaluation
- Final score = percentage of characteristics that pass

### 3. Experiments
- Create experiments with:
  - Custom extraction prompt
  - Structured JSON schema for output
  - Model selection
- Edit existing experiments
- Multiple experiments in tabs

### 4. Evaluation System
- Run evaluations using any judge on any experiment
- Real-time progress tracking with Server-Sent Events
- For each transcript:
  - Extract structured data using experiment prompt/schema
  - Judge evaluates both transcript + extracted data
  - Each characteristic votes (pass/fail)
  - Final score calculated
- View leaderboard ranking experiments by average score

## Architecture

### Frontend (Next.js + shadcn/ui)
- **Framework**: Next.js 15 with App Router
- **UI**: shadcn/ui components + TailwindCSS
- **State**: React Query for server state
- **Editor**: Monaco Editor for JSON schema editing

### Backend (FastAPI + SQLite)
- **Framework**: FastAPI with async SQLAlchemy
- **Database**: SQLite with async support
- **LLM Integration**: OpenAI Python SDK
- **Real-time**: Server-Sent Events for evaluation progress

## Setup

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- OpenAI API key

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
```

5. Add your OpenAI API key to `.env`:
```env
OPENAI_API_KEY=sk-your-api-key-here
```

6. Run the backend:
```bash
python main.py
```

The API will be available at http://localhost:8000
- API docs: http://localhost:8000/docs

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Usage Workflow

### 1. View Transcripts
- Navigate to the "Transcripts" tab
- Click on any transcript to view its content
- Use "Compare" to view two transcripts side-by-side
- Click "Add" to manually add a new transcript

### 2. Create a Judge
- Navigate to the "Judges" tab
- Click "Create Judge"
- Select a model (e.g., gpt-4o)
- Add characteristics:
  - Name: e.g., "Completeness"
  - Prompt: Define what makes the extraction complete
- The judge will evaluate extractions based on these characteristics

### 3. Create an Experiment
- Navigate to the "Experiments" tab
- Click "New Experiment"
- Define:
  - Name: e.g., "Client Details Extraction v1"
  - Model: Select the LLM to use for extraction
  - Prompt: Instructions for what to extract
  - Schema: JSON schema defining the structure
- Monaco Editor provides JSON validation

### 4. Run an Evaluation
- Open an experiment
- Click "Run Evaluation"
- Select a judge
- Watch real-time progress as the system:
  1. Extracts data from each transcript
  2. Evaluates each characteristic
  3. Calculates final scores
- View results in the leaderboard

### 5. Compare Results
- The leaderboard shows all evaluations ranked by score
- Use different judges to compare evaluation approaches
- Iterate on your extraction prompt and schema

## Database Schema

The app uses SQLite with the following tables:

- **transcripts**: Imported and manual transcripts
- **judges**: LLM judge configurations
- **characteristics**: Boolean evaluation criteria for judges
- **experiments**: Extraction prompt + schema + model
- **evaluations**: Evaluation runs (experiment + judge)
- **evaluation_results**: Per-transcript results
- **characteristic_votes**: Individual characteristic evaluations

## API Endpoints

### Transcripts
- `GET /api/transcripts` - List all transcripts
- `POST /api/transcripts` - Add new transcript
- `GET /api/transcripts/{id}` - Get transcript details
- `DELETE /api/transcripts/{id}` - Delete transcript

### Judges
- `GET /api/judges` - List all judges
- `POST /api/judges` - Create judge
- `POST /api/judges/{id}/characteristics` - Add characteristic
- `DELETE /api/characteristics/{id}` - Delete characteristic

### Experiments
- `GET /api/experiments` - List all experiments
- `POST /api/experiments` - Create experiment
- `PUT /api/experiments/{id}` - Update experiment
- `GET /api/experiments/{id}/leaderboard` - Get leaderboard

### Evaluations
- `POST /api/evaluations/run` - Start evaluation
- `GET /api/evaluations/{id}` - Get evaluation results
- `GET /api/evaluations/{id}/stream` - Stream progress (SSE)

### Models
- `GET /api/models` - List available OpenAI models

## Tech Stack

### Frontend
- Next.js 15 (App Router)
- TypeScript
- shadcn/ui components
- TailwindCSS
- React Query
- Monaco Editor
- lucide-react icons

### Backend
- FastAPI
- SQLAlchemy (async)
- SQLite with aiosqlite
- Pydantic
- OpenAI Python SDK
- Server-Sent Events

## Directory Structure

```
app/
├── frontend/
│   ├── app/
│   │   ├── transcripts/page.tsx
│   │   ├── judges/page.tsx
│   │   ├── experiments/page.tsx
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/ (shadcn components)
│   │   └── (feature components)
│   └── lib/
│       ├── api.ts
│       └── utils.ts
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── config.py
│   ├── routers/
│   │   ├── transcripts.py
│   │   ├── judges.py
│   │   ├── experiments.py
│   │   └── evaluations.py
│   └── services/
│       ├── llm_service.py
│       ├── evaluation_service.py
│       └── transcript_service.py
└── docs/
    └── plan.md
```

## Development

### Backend Development
```bash
cd backend
uvicorn main:app --reload
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Database Reset
To reset the database, simply delete `backend/app.db` and restart the backend.

## Troubleshooting

### Backend Issues
- **Database errors**: Delete `app.db` and restart
- **OpenAI API errors**: Check your API key in `.env`
- **Import errors**: Ensure virtual environment is activated

### Frontend Issues
- **Module not found**: Run `npm install`
- **API connection errors**: Ensure backend is running on port 8000
- **Type errors**: Check TypeScript configuration

## Future Enhancements

- Export evaluation results to CSV/JSON
- Batch import transcripts
- Custom scoring functions
- Comparison of multiple experiments
- Historical trend analysis
- Fine-tuning support

## License

This project is part of the TestTask transcript generation system.
