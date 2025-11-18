from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, get_db
from config import settings
from routers import transcripts, judges, experiments, evaluations, ai_assist
from services.transcript_service import load_transcripts_from_folder
from services.llm_service import get_available_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database and load transcripts
    await init_db()
    async for db in get_db():
        await load_transcripts_from_folder(db)
        break
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Transcript Analysis & LLM Evaluation API",
    description="API for analyzing transcripts and evaluating LLM extractions",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transcripts.router)
app.include_router(judges.router)
app.include_router(experiments.router)
app.include_router(evaluations.router)
app.include_router(ai_assist.router)


@app.get("/")
async def root():
    return {
        "message": "Transcript Analysis & LLM Evaluation API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/api/models")
async def list_models():
    """List available OpenAI models"""
    try:
        models = await get_available_models()
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=False)
