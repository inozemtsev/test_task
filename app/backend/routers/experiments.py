import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import Experiment, Evaluation, EvaluationResult
from schemas import (
    ExperimentCreate,
    ExperimentUpdate,
    ExperimentResponse,
    SchemaValidationRequest,
    SchemaValidationResponse,
    LeaderboardEntry,
)

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentResponse])
async def list_experiments(db: AsyncSession = Depends(get_db)):
    """List all experiments"""
    result = await db.execute(
        select(Experiment).order_by(Experiment.created_at.desc())
    )
    experiments = result.scalars().all()
    return experiments


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific experiment by ID"""
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return experiment


@router.post("", response_model=ExperimentResponse)
async def create_experiment(
    experiment_data: ExperimentCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new experiment"""
    # Validate JSON schema
    try:
        schema = json.loads(experiment_data.schema_json)

        # Validate schema structure for OpenAI structured outputs
        if not isinstance(schema, dict):
            raise HTTPException(status_code=400, detail="Schema must be a JSON object")

        if "name" not in schema:
            raise HTTPException(status_code=400, detail="Schema must have a 'name' field")

        if "schema" not in schema:
            raise HTTPException(
                status_code=400,
                detail="Schema must have a 'schema' field containing the JSON schema definition"
            )

        # Ensure strict mode is set
        if "strict" not in schema:
            schema["strict"] = True
            experiment_data.schema_json = json.dumps(schema)

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    experiment = Experiment(
        name=experiment_data.name,
        prompt=experiment_data.prompt,
        schema_json=experiment_data.schema_json,
        model=experiment_data.model,
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return experiment


@router.put("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: int,
    experiment_data: ExperimentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an experiment"""
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment_data.name is not None:
        experiment.name = experiment_data.name
    if experiment_data.prompt is not None:
        experiment.prompt = experiment_data.prompt
    if experiment_data.schema_json is not None:
        try:
            schema = json.loads(experiment_data.schema_json)

            # Validate schema structure for OpenAI structured outputs
            if not isinstance(schema, dict):
                raise HTTPException(status_code=400, detail="Schema must be a JSON object")

            if "name" not in schema:
                raise HTTPException(status_code=400, detail="Schema must have a 'name' field")

            if "schema" not in schema:
                raise HTTPException(
                    status_code=400,
                    detail="Schema must have a 'schema' field containing the JSON schema definition"
                )

            # Ensure strict mode is set
            if "strict" not in schema:
                schema["strict"] = True
                experiment_data.schema_json = json.dumps(schema)

            experiment.schema_json = experiment_data.schema_json
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid JSON: {str(e)}"
            )
    if experiment_data.model is not None:
        experiment.model = experiment_data.model
    if experiment_data.enable_two_pass is not None:
        experiment.enable_two_pass = experiment_data.enable_two_pass

    await db.commit()
    await db.refresh(experiment)
    return experiment


@router.delete("/{experiment_id}")
async def delete_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an experiment"""
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    await db.delete(experiment)
    await db.commit()
    return {"message": "Experiment deleted successfully"}


@router.post("/validate-schema", response_model=SchemaValidationResponse)
async def validate_schema(request: SchemaValidationRequest):
    """Validate a JSON schema"""
    try:
        json.loads(request.schema_content)
        return SchemaValidationResponse(valid=True)
    except json.JSONDecodeError as e:
        return SchemaValidationResponse(valid=False, error=str(e))


@router.get("/{experiment_id}/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(experiment_id: int, db: AsyncSession = Depends(get_db)):
    """Get leaderboard for an experiment (evaluations by different judges) with global metrics"""
    # Get all completed evaluations for this experiment
    query = (
        select(Evaluation)
        .where(Evaluation.experiment_id == experiment_id)
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
