from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from database import get_db
from models import Judge, Characteristic, Evaluation, EvaluationResult, Experiment
from schemas import (
    JudgeCreate,
    JudgeUpdate,
    JudgeResponse,
    CharacteristicCreate,
    CharacteristicResponse,
    LeaderboardEntry,
)
from collections import defaultdict

router = APIRouter(prefix="/api/judges", tags=["judges"])


@router.get("", response_model=list[JudgeResponse])
async def list_judges(db: AsyncSession = Depends(get_db)):
    """List all judges with their characteristics"""
    result = await db.execute(
        select(Judge)
        .options(selectinload(Judge.characteristics))
        .order_by(Judge.created_at.desc())
    )
    judges = result.scalars().all()
    return judges


@router.get("/{judge_id}", response_model=JudgeResponse)
async def get_judge(judge_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific judge by ID"""
    result = await db.execute(
        select(Judge)
        .options(selectinload(Judge.characteristics))
        .where(Judge.id == judge_id)
    )
    judge = result.scalar_one_or_none()

    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")

    return judge


@router.post("", response_model=JudgeResponse)
async def create_judge(judge_data: JudgeCreate, db: AsyncSession = Depends(get_db)):
    """Create a new judge"""
    judge = Judge(name=judge_data.name, model=judge_data.model)
    db.add(judge)
    await db.commit()
    await db.refresh(judge)

    # Re-fetch with characteristics loaded
    result = await db.execute(
        select(Judge)
        .options(selectinload(Judge.characteristics))
        .where(Judge.id == judge.id)
    )
    return result.scalar_one()


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

    await db.commit()
    await db.refresh(judge)

    # Re-fetch with characteristics loaded
    result = await db.execute(
        select(Judge)
        .options(selectinload(Judge.characteristics))
        .where(Judge.id == judge.id)
    )
    return result.scalar_one()


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


@router.post("/{judge_id}/characteristics", response_model=CharacteristicResponse)
async def add_characteristic(
    judge_id: int,
    characteristic_data: CharacteristicCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a characteristic to a judge"""
    import json

    result = await db.execute(select(Judge).where(Judge.id == judge_id))
    judge = result.scalar_one_or_none()

    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")

    # Validate schema_json if provided
    if characteristic_data.schema_json:
        if isinstance(characteristic_data.schema_json, str) and characteristic_data.schema_json.strip():
            try:
                json.loads(characteristic_data.schema_json)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON schema: {str(e)}")
        else:
            # If schema_json is empty or not a string, set it to None
            characteristic_data.schema_json = None

    characteristic = Characteristic(
        judge_id=judge_id,
        name=characteristic_data.name,
        prompt=characteristic_data.prompt,
        schema_json=characteristic_data.schema_json,
    )
    db.add(characteristic)
    await db.commit()
    await db.refresh(characteristic)
    return characteristic


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


@router.delete("/characteristics/{characteristic_id}")
async def delete_characteristic(
    characteristic_id: int, db: AsyncSession = Depends(get_db)
):
    """Delete a characteristic and all associated votes"""
    from models import CharacteristicVote
    from sqlalchemy.orm import selectinload

    # Load characteristic with votes to ensure cascade delete works
    result = await db.execute(
        select(Characteristic)
        .options(selectinload(Characteristic.votes))
        .where(Characteristic.id == characteristic_id)
    )
    characteristic = result.scalar_one_or_none()

    if not characteristic:
        raise HTTPException(status_code=404, detail="Characteristic not found")

    await db.delete(characteristic)
    await db.commit()
    return {"message": "Characteristic deleted successfully"}
