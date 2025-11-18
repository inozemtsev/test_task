from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import Judge, Evaluation, EvaluationResult, Experiment
from schemas import (
    JudgeCreate,
    JudgeUpdate,
    JudgeResponse,
    LeaderboardEntry,
)

router = APIRouter(prefix="/api/judges", tags=["judges"])


@router.get("", response_model=list[JudgeResponse])
async def list_judges(db: AsyncSession = Depends(get_db)):
    """List all judges"""
    result = await db.execute(
        select(Judge).order_by(Judge.created_at.desc())
    )
    judges = result.scalars().all()
    return judges


@router.get("/{judge_id}", response_model=JudgeResponse)
async def get_judge(judge_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific judge by ID"""
    result = await db.execute(
        select(Judge).where(Judge.id == judge_id)
    )
    judge = result.scalar_one_or_none()

    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")

    return judge


@router.post("", response_model=JudgeResponse)
async def create_judge(judge_data: JudgeCreate, db: AsyncSession = Depends(get_db)):
    """Create a new judge"""
    # Convert judge_config Pydantic model to dict if provided
    judge_config_dict = None
    if judge_data.judge_config:
        judge_config_dict = judge_data.judge_config.dict()

    judge = Judge(
        name=judge_data.name,
        model=judge_data.model,
        judge_config=judge_config_dict
    )
    db.add(judge)
    await db.commit()
    await db.refresh(judge)
    return judge


@router.put("/{judge_id}", response_model=JudgeResponse)
async def update_judge(
    judge_id: int, judge_data: JudgeUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a judge"""
    result = await db.execute(select(Judge).where(Judge.id == judge_id))
    judge = result.scalar_one_or_none()

    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")

    if judge_data.name is not None:
        judge.name = judge_data.name
    if judge_data.model is not None:
        judge.model = judge_data.model
    if judge_data.judge_config is not None:
        # Convert Pydantic model to dict
        judge.judge_config = judge_data.judge_config.dict()

    await db.commit()
    await db.refresh(judge)
    return judge


@router.delete("/{judge_id}")
async def delete_judge(judge_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a judge"""
    result = await db.execute(select(Judge).where(Judge.id == judge_id))
    judge = result.scalar_one_or_none()

    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")

    await db.delete(judge)
    await db.commit()
    return {"message": "Judge deleted successfully"}


@router.get("/{judge_id}/leaderboard", response_model=list[LeaderboardEntry])
async def get_judge_leaderboard(judge_id: int, db: AsyncSession = Depends(get_db)):
    """Get leaderboard for a judge (experiments ranked by score)"""
    # Query to get average scores for each experiment evaluated by this judge
    query = (
        select(
            Evaluation.id.label("evaluation_id"),
            Evaluation.judge_id,
            Evaluation.experiment_id,
            Experiment.name.label("experiment_name"),
            Evaluation.completed_at,
            Evaluation.schema_stability,
            func.avg(EvaluationResult.final_score).label("avg_score"),
            func.count(EvaluationResult.id).label("num_transcripts"),
        )
        .join(Experiment, Evaluation.experiment_id == Experiment.id)
        .join(EvaluationResult, Evaluation.id == EvaluationResult.evaluation_id)
        .where(Evaluation.judge_id == judge_id)
        .where(Evaluation.status == "completed")
        .group_by(Evaluation.id)
        .order_by(func.avg(EvaluationResult.final_score).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    leaderboard = []
    for row in rows:
        entry = LeaderboardEntry(
            experiment_id=row.experiment_id,
            experiment_name=row.experiment_name,
            avg_score=float(row.avg_score) if row.avg_score else 0.0,
            num_transcripts=row.num_transcripts,
            evaluation_id=row.evaluation_id,
            completed_at=row.completed_at,
            schema_stability=row.schema_stability,
        )
        leaderboard.append(entry)

    return leaderboard
