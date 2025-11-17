# Implementation Plan: Transcript Analysis & LLM Evaluation App

## Architecture Overview

**Frontend**: Next.js 14+ (App Router) + shadcn/ui + TailwindCSS
**Backend**: Python FastAPI + SQLite + SQLAlchemy ORM
**Communication**: REST API

## Tech Stack Details

### Frontend
- Next.js 14+ (App Router)
- shadcn/ui components
- TailwindCSS
- React Query (data fetching/caching)
- Zod (schema validation)
- Monaco Editor (JSON editing with validation)

### Backend
- FastAPI
- SQLAlchemy (ORM)
- SQLite (database)
- Pydantic (validation)
- OpenAI Python SDK
- Alembic (migrations)

## Database Schema (SQLite)

```sql
-- Transcripts
transcripts (id, name, content, created_at, updated_at, source)

-- Experiments (prompt + schema + model)
experiments (id, name, prompt, schema_json, model, created_at, updated_at)

-- LLM Judges
judges (id, name, model, created_at, updated_at)

-- Judge Characteristics (boolean criteria)
characteristics (id, judge_id, name, prompt, created_at)

-- Evaluation Runs
evaluations (id, experiment_id, judge_id, status, started_at, completed_at)

-- Evaluation Results (per transcript)
evaluation_results (id, evaluation_id, transcript_id, extracted_data, characteristic_votes, final_score, created_at)

-- Characteristic Votes
characteristic_votes (id, evaluation_result_id, characteristic_id, vote, reasoning)
```

## Frontend Structure

```
app/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx (redirects to /transcripts)
│   │   ├── transcripts/
│   │   │   └── page.tsx (Tab 1: Transcript Viewer)
│   │   ├── judges/
│   │   │   └── page.tsx (Tab 2: LLM Judge Config)
│   │   └── experiments/
│   │       └── page.tsx (Tab 3: Experiments & Evaluations)
│   ├── components/
│   │   ├── ui/ (shadcn components)
│   │   ├── TranscriptViewer.tsx
│   │   ├── TranscriptComparison.tsx
│   │   ├── AddTranscriptForm.tsx
│   │   ├── JudgeForm.tsx
│   │   ├── CharacteristicForm.tsx
│   │   ├── ExperimentForm.tsx
│   │   ├── JSONSchemaEditor.tsx
│   │   ├── EvaluationRunner.tsx
│   │   └── Leaderboard.tsx
│   ├── lib/
│   │   ├── api.ts (API client functions)
│   │   └── utils.ts
│   └── package.json
```

## Backend Structure

```
app/
├── backend/
│   ├── main.py (FastAPI app)
│   ├── database.py (SQLAlchemy setup)
│   ├── models.py (SQLAlchemy models)
│   ├── schemas.py (Pydantic schemas)
│   ├── routers/
│   │   ├── transcripts.py
│   │   ├── judges.py
│   │   ├── experiments.py
│   │   └── evaluations.py
│   ├── services/
│   │   ├── llm_service.py (OpenAI integration)
│   │   ├── evaluation_service.py (run evaluations)
│   │   └── transcript_service.py
│   ├── config.py (settings, API keys)
│   └── requirements.txt
└── docs/
    └── plan.md (this file)
```

## API Endpoints

### Transcripts
- `GET /api/transcripts` - List all transcripts
- `GET /api/transcripts/{id}` - Get transcript by ID
- `POST /api/transcripts` - Add new transcript
- `DELETE /api/transcripts/{id}` - Delete transcript

### Judges
- `GET /api/judges` - List all judges
- `GET /api/judges/{id}` - Get judge details with characteristics
- `POST /api/judges` - Create judge
- `PUT /api/judges/{id}` - Update judge
- `DELETE /api/judges/{id}` - Delete judge
- `POST /api/judges/{id}/characteristics` - Add characteristic
- `DELETE /api/characteristics/{id}` - Delete characteristic

### Experiments
- `GET /api/experiments` - List all experiments
- `GET /api/experiments/{id}` - Get experiment details
- `POST /api/experiments` - Create experiment
- `PUT /api/experiments/{id}` - Update experiment
- `DELETE /api/experiments/{id}` - Delete experiment
- `POST /api/experiments/validate-schema` - Validate JSON schema

### Evaluations
- `POST /api/evaluations/run` - Start evaluation (experiment_id + judge_id)
- `GET /api/evaluations/{id}` - Get evaluation status and results
- `GET /api/evaluations/{id}/stream` - SSE for real-time progress
- `GET /api/experiments/{id}/leaderboard` - Get leaderboard for experiment

## Implementation Steps

### Phase 1: Project Setup (Week 1)
1. Create directory structure ✅
2. Initialize Next.js frontend with shadcn/ui
3. Setup Python FastAPI backend
4. Configure SQLite database and models
5. Setup CORS, environment variables

### Phase 2: Transcript Management (Week 1-2)
1. Backend: Load existing transcripts from `/transcripts` folder into DB
2. Backend: Implement transcript CRUD endpoints
3. Frontend: Transcript list view with click-to-read
4. Frontend: Side-by-side comparison (2 transcript selector)
5. Frontend: Add transcript form (collapsible)

### Phase 3: LLM Judge System (Week 2)
1. Backend: Judge and Characteristic models/endpoints
2. Backend: Fetch available models from OpenAI API
3. Frontend: Judge creation form
4. Frontend: Add/remove characteristics with prompts
5. Frontend: Judge list and detail views

### Phase 4: Experiment System (Week 2-3)
1. Backend: Experiment CRUD endpoints
2. Backend: JSON schema validation endpoint
3. Frontend: Experiment creation form
4. Frontend: Monaco Editor for JSON schema with validation
5. Frontend: Multiple experiment tabs
6. Backend: LLM service for structured extraction

### Phase 5: Evaluation System (Week 3-4)
1. Backend: Evaluation orchestration service
2. Backend: For each transcript:
   - Extract data using experiment prompt/schema
   - Pass transcript + extracted data to judge
   - Collect characteristic votes
   - Calculate final score (majority vote)
3. Backend: SSE endpoint for real-time progress
4. Frontend: Evaluation runner UI with progress
5. Frontend: Leaderboard showing experiments ranked by average score

### Phase 6: Polish & Testing (Week 4)
1. Error handling and loading states
2. UI/UX improvements
3. Testing with real transcripts
4. Documentation
5. Deployment setup

## Key Features Detail

### 1. Transcript Side-by-Side View
- Two dropdowns to select transcripts
- Split-pane layout (50/50) with synchronized scrolling option
- Highlighting for search/comparison

### 2. LLM Judge Logic
- Each characteristic is evaluated independently (boolean: pass/fail)
- Judge prompt includes: transcript + extracted JSON + characteristic question
- Final score = percentage of characteristics that passed
- Store individual votes and reasoning for transparency

### 3. Evaluation Process
```python
for transcript in transcripts:
    # Step 1: Extract using experiment
    extracted = llm_call(experiment.prompt, transcript, experiment.schema)

    # Step 2: Evaluate each characteristic
    votes = []
    for char in judge.characteristics:
        prompt = f"{char.prompt}\n\nTranscript: {transcript}\n\nExtracted: {extracted}"
        vote = llm_call(prompt, model=judge.model)  # Returns boolean
        votes.append(vote)

    # Step 3: Calculate score
    score = sum(votes) / len(votes)
```

### 4. Leaderboard
- Grouped by judge
- Ranked by average score across all transcripts
- Shows: experiment name, avg score, num transcripts, timestamp
- Expandable to see per-transcript results

## Configuration

### Backend (.env)
```
OPENAI_API_KEY=sk-...
DATABASE_URL=sqlite:///./app.db
TRANSCRIPTS_PATH=../transcripts
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Requirements Clarifications

Based on user answers:
- **Judge Evaluation Target**: Judge receives both the original transcript AND the extracted structured data, evaluating extraction quality
- **Data Storage**: SQLite database for persistence
- **Leaderboard**: Compares different experiments (prompts/schemas) using the same judge
- **API Key**: Configured globally on backend via environment variable

## Testing Strategy
- Unit tests for evaluation logic
- Integration tests for API endpoints
- E2E tests for critical user flows
- Manual testing with existing transcripts from `/transcripts` folder

## Deployment
- Frontend: Vercel/Netlify
- Backend: Docker container (Railway/Render)
- Database: SQLite file in persistent volume
