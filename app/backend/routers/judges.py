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
    """Get leaderboard for a judge (experiments ranked by score) with global metrics"""
    # Get all completed evaluations for this judge
    query = (
        select(Evaluation)
        .where(Evaluation.judge_id == judge_id)
        .where(Evaluation.status == "completed")
    )
    result = await db.execute(query)
    evaluations = result.scalars().all()

    leaderboard = []
    for evaluation in evaluations:
        # Get experiment name
        exp_result = await db.execute(
            select(Experiment).where(Experiment.id == evaluation.experiment_id)
        )
        experiment = exp_result.scalar_one()

        # Get all results for this evaluation
        results_query = await db.execute(
            select(EvaluationResult)
            .where(EvaluationResult.evaluation_id == evaluation.id)
        )
        results = results_query.scalars().all()

        if not results:
            continue

        # Calculate global metrics by aggregating TP/FP/FN across all transcripts
        total_tp = 0
        total_fp = 0
        total_fn = 0
        avg_scores = []

        for result in results:
            if result.judge_result:
                # Count TP/FP/FN from in-scope facts only
                tp = len([f for f in result.judge_result.get('predicted_facts', [])
                         if f.get('status') == 'TP' and f.get('in_scope', True)])
                fp = len([f for f in result.judge_result.get('predicted_facts', [])
                         if f.get('status') == 'FP' and f.get('in_scope', True)])
                fn = len([f for f in result.judge_result.get('gold_facts', [])
                         if f.get('status') == 'FN' and f.get('in_scope', True)])

                total_tp += tp
                total_fp += fp
                total_fn += fn

            if result.final_score is not None:
                avg_scores.append(result.final_score)

        # Calculate global metrics
        global_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        global_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        global_f1 = (2 * global_precision * global_recall) / (global_precision + global_recall) if (global_precision + global_recall) > 0 else 0.0

        entry = LeaderboardEntry(
            experiment_id=evaluation.experiment_id,
            experiment_name=experiment.name,
            avg_score=sum(avg_scores) / len(avg_scores) if avg_scores else 0.0,
            num_transcripts=len(results),
            evaluation_id=evaluation.id,
            completed_at=evaluation.completed_at,
            schema_stability=evaluation.schema_stability,
            global_precision=global_precision,
            global_recall=global_recall,
            global_f1=global_f1,
            total_tp=total_tp,
            total_fp=total_fp,
            total_fn=total_fn,
        )
        leaderboard.append(entry)

    # Sort by global F1 (descending)
    leaderboard.sort(key=lambda x: x.global_f1, reverse=True)

    return leaderboard
