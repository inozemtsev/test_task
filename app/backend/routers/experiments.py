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
    """Get leaderboard for an experiment (evaluations by different judges)"""
    # Query to get average scores for each evaluation
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
        .where(Evaluation.experiment_id == experiment_id)
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
