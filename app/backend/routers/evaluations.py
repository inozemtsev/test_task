import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_db
from models import Evaluation, EvaluationResult
from schemas import EvaluationRunRequest, EvaluationResponse, EvaluationResultResponse
from services.evaluation_service import run_evaluation, progress_tracker

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


@router.post("/run", response_model=EvaluationResponse)
async def start_evaluation(
    request: EvaluationRunRequest, db: AsyncSession = Depends(get_db)
):
    """Start a new evaluation"""
    # Create evaluation record
    evaluation = Evaluation(
        experiment_id=request.experiment_id,
        judge_id=request.judge_id,
        status="pending",
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)

    # Re-fetch with relationships loaded
    result = await db.execute(
        select(Evaluation)
        .options(selectinload(Evaluation.results))
        .where(Evaluation.id == evaluation.id)
    )
    evaluation = result.scalar_one()

    # Run evaluation in background with optional transcript filter
    asyncio.create_task(run_evaluation(evaluation.id, request.transcript_ids))

    return evaluation


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(evaluation_id: int, db: AsyncSession = Depends(get_db)):
    """Get evaluation status and results"""
    from models import Transcript

    result = await db.execute(
        select(Evaluation)
        .options(
            selectinload(Evaluation.results)
            .selectinload(EvaluationResult.transcript)
        )
        .where(Evaluation.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Transform results to include transcript names
    evaluation_response = EvaluationResponse(
        id=evaluation.id,
        experiment_id=evaluation.experiment_id,
        judge_id=evaluation.judge_id,
        status=evaluation.status,
        started_at=evaluation.started_at,
        completed_at=evaluation.completed_at,
        schema_stability=evaluation.schema_stability,
        results=[],
    )

    for result in evaluation.results:
        eval_result_response = EvaluationResultResponse(
            id=result.id,
            transcript_id=result.transcript_id,
            transcript_name=result.transcript.name,
            extracted_data=result.extracted_data,
            initial_extraction=result.initial_extraction,
            review_data=result.review_data,
            final_extraction=result.final_extraction,
            judge_result=result.judge_result,
            schema_overlap_data=result.schema_overlap_data,
            final_score=result.final_score,
        )
        evaluation_response.results.append(eval_result_response)

    return evaluation_response


@router.get("/{evaluation_id}/stream")
async def stream_evaluation_progress(evaluation_id: int):
    """Stream evaluation progress using Server-Sent Events"""

    async def event_generator():
        while True:
            if evaluation_id in progress_tracker:
                progress = progress_tracker[evaluation_id]

                data = {
                    "current": progress.current_transcript,
                    "total": progress.total_transcripts,
                    "status": progress.current_status,
                    "error": progress.error,
                }

                yield f"data: {json.dumps(data)}\n\n"

                if progress.current_status in ["completed", "failed"]:
                    # Clean up progress tracker
                    del progress_tracker[evaluation_id]
                    break
            else:
                yield f"data: {json.dumps({'status': 'pending'})}\n\n"

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )
