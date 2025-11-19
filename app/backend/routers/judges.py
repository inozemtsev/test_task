from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import Judge, Evaluation, EvaluationResult, Experiment, GroundTruth, Transcript
from schemas import (
    JudgeCreate,
    JudgeUpdate,
    JudgeResponse,
    LeaderboardEntry,
    GroundTruthGenerateRequest,
    GroundTruthDetailResponse,
    GroundTruthUpdateRequest,
    TranscriptResponse,
)
from services.ground_truth_service import (
    regenerate_ground_truth_for_transcripts,
)

router = APIRouter(prefix="/api/judges", tags=["judges"])


async def _get_judge_or_404(judge_id: int, db: AsyncSession) -> Judge:
    result = await db.execute(select(Judge).where(Judge.id == judge_id))
    judge = result.scalar_one_or_none()
    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")
    return judge


async def _build_ground_truth_response(
    judge_id: int,
    transcript_id: int,
    db: AsyncSession,
) -> GroundTruthDetailResponse:
    transcript_result = await db.execute(
        select(Transcript).where(Transcript.id == transcript_id)
    )
    transcript = transcript_result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    gt_result = await db.execute(
        select(GroundTruth).where(
            GroundTruth.judge_id == judge_id,
            GroundTruth.transcript_id == transcript_id,
        )
    )
    ground_truth = gt_result.scalar_one_or_none()

    transcript_payload = TranscriptResponse.model_validate(transcript)
    return GroundTruthDetailResponse(
        transcript=transcript_payload,
        ground_truth=ground_truth.data if ground_truth else None,
        updated_at=ground_truth.updated_at if ground_truth else None,
    )


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
    judge = await _get_judge_or_404(judge_id, db)

    await db.delete(judge)
    await db.commit()
    return {"message": "Judge deleted successfully"}


@router.post("/{judge_id}/ground-truth/generate")
async def generate_ground_truth_endpoint(
    judge_id: int,
    payload: GroundTruthGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate and store ground truth for all (or selected) transcripts."""
    judge = await _get_judge_or_404(judge_id, db)

    transcript_query = select(Transcript)
    if payload.transcript_ids:
        transcript_query = transcript_query.where(Transcript.id.in_(payload.transcript_ids))

    transcript_result = await db.execute(transcript_query)
    transcripts = transcript_result.scalars().all()

    if not transcripts:
        raise HTTPException(status_code=404, detail="No transcripts found for generation")

    return await regenerate_ground_truth_for_transcripts(db, judge, transcripts)


@router.get(
    "/{judge_id}/ground-truth/{transcript_id}",
    response_model=GroundTruthDetailResponse,
)
async def get_ground_truth_detail(
    judge_id: int,
    transcript_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch transcript + stored ground truth for inspection/editing."""
    await _get_judge_or_404(judge_id, db)
    return await _build_ground_truth_response(judge_id, transcript_id, db)


@router.put(
    "/{judge_id}/ground-truth/{transcript_id}",
    response_model=GroundTruthDetailResponse,
)
async def update_ground_truth(
    judge_id: int,
    transcript_id: int,
    payload: GroundTruthUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create or update stored ground truth for a transcript."""
    await _get_judge_or_404(judge_id, db)

    ground_truth_data = payload.ground_truth
    if not isinstance(ground_truth_data, list):
        raise HTTPException(
            status_code=400,
            detail="Ground truth must be a JSON array of fact objects.",
        )

    transcript_result = await db.execute(
        select(Transcript).where(Transcript.id == transcript_id)
    )
    transcript = transcript_result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    gt_result = await db.execute(
        select(GroundTruth).where(
            GroundTruth.judge_id == judge_id,
            GroundTruth.transcript_id == transcript_id,
        )
    )
    ground_truth = gt_result.scalar_one_or_none()

    if ground_truth:
        ground_truth.data = ground_truth_data
    else:
        ground_truth = GroundTruth(
            judge_id=judge_id,
            transcript_id=transcript_id,
            data=ground_truth_data,
        )
        db.add(ground_truth)

    await db.commit()

    return await _build_ground_truth_response(judge_id, transcript_id, db)


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
