import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
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
from collections import defaultdict

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
        # Create base entry
        entry = {
            "experiment_id": row.experiment_id,
            "experiment_name": row.experiment_name,
            "avg_score": float(row.avg_score) if row.avg_score else 0.0,
            "num_transcripts": row.num_transcripts,
            "evaluation_id": row.evaluation_id,
            "completed_at": row.completed_at,
        }

        # Fetch detailed results to aggregate metrics and schema stability
        from models import CharacteristicVote
        results_query = await db.execute(
            select(EvaluationResult)
            .options(
                selectinload(EvaluationResult.characteristic_votes)
                .selectinload(CharacteristicVote.characteristic)  # Load characteristic to get name
            )
            .where(EvaluationResult.evaluation_id == row.evaluation_id)
        )
        results_list = results_query.scalars().all()

        # Calculate avg schema stability
        overlaps = [
            r.schema_overlap_percentage
            for r in results_list
            if r.schema_overlap_percentage is not None
        ]
        entry["avg_schema_overlap"] = (
            sum(overlaps) / len(overlaps) if overlaps else None
        )

        # Aggregate metrics across all characteristic votes
        all_metrics = defaultdict(list)
        characteristic_results = defaultdict(lambda: {"passes": 0, "fails": 0, "metrics": defaultdict(lambda: {"numerators": [], "denominators": [], "values": []})})

        for result in results_list:
            for vote in result.characteristic_votes:
                char_name = vote.characteristic.name

                # Track pass/fail
                if vote.vote:
                    characteristic_results[char_name]["passes"] += 1
                else:
                    characteristic_results[char_name]["fails"] += 1

                # Check for top-level numerator/denominator in result_data
                if vote.result_data and "numerator" in vote.result_data and "denominator" in vote.result_data:
                    key = "score"  # Use "score" as the default key for top-level numerator/denominator
                    all_metrics[key].append({
                        "numerator": vote.result_data["numerator"],
                        "denominator": vote.result_data["denominator"]
                    })
                    characteristic_results[char_name]["metrics"][key]["numerators"].append(vote.result_data["numerator"])
                    characteristic_results[char_name]["metrics"][key]["denominators"].append(vote.result_data["denominator"])

                # Aggregate metrics from metrics field
                if vote.metrics:
                    for key, value in vote.metrics.items():
                        all_metrics[key].append(value)

                        # Check if value is numerator/denominator or simple float
                        if isinstance(value, dict) and "numerator" in value and "denominator" in value:
                            characteristic_results[char_name]["metrics"][key]["numerators"].append(value["numerator"])
                            characteristic_results[char_name]["metrics"][key]["denominators"].append(value["denominator"])
                        elif isinstance(value, (int, float)):
                            characteristic_results[char_name]["metrics"][key]["values"].append(value)

        # Process avg_metrics: handle both numerator/denominator and regular floats
        avg_metrics = {}
        for key, values in all_metrics.items():
            if values:
                first_val = values[0]
                if isinstance(first_val, dict) and "numerator" in first_val and "denominator" in first_val:
                    # Sum numerators and denominators
                    total_numerator = sum(v["numerator"] for v in values if isinstance(v, dict))
                    total_denominator = sum(v["denominator"] for v in values if isinstance(v, dict))
                    avg_metrics[key] = {
                        "numerator": total_numerator,
                        "denominator": total_denominator
                    }
                elif isinstance(first_val, (int, float)):
                    # Average regular floats
                    avg_metrics[key] = sum(v for v in values if isinstance(v, (int, float))) / len([v for v in values if isinstance(v, (int, float))])

        entry["avg_metrics"] = avg_metrics if avg_metrics else None

        # Process characteristic_results: create final aggregated results per characteristic
        final_char_results = {}
        for char_name, data in characteristic_results.items():
            char_result = {}
            total_tests = data["passes"] + data["fails"]

            # Add pass/fail info
            char_result["passes"] = data["passes"]
            char_result["fails"] = data["fails"]
            char_result["total"] = total_tests

            # Add aggregated metrics for this characteristic
            if data["metrics"]:
                char_metrics = {}
                for metric_key, metric_data in data["metrics"].items():
                    if metric_data["numerators"] and metric_data["denominators"]:
                        # Sum numerators and denominators
                        char_metrics[metric_key] = {
                            "numerator": sum(metric_data["numerators"]),
                            "denominator": sum(metric_data["denominators"])
                        }
                    elif metric_data["values"]:
                        # Average regular values
                        char_metrics[metric_key] = sum(metric_data["values"]) / len(metric_data["values"])

                if char_metrics:
                    char_result["metrics"] = char_metrics

            final_char_results[char_name] = char_result

        entry["characteristic_results"] = final_char_results if final_char_results else None

        leaderboard.append(LeaderboardEntry(**entry))

    return leaderboard
