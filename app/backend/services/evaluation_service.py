from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import (
    Evaluation,
    EvaluationResult,
    CharacteristicVote,
    Transcript,
    Experiment,
    Judge,
    Characteristic,
)
from services.llm_service import extract_structured_data, evaluate_characteristic, calculate_schema_overlap
from datetime import datetime
import asyncio


class EvaluationProgress:
    """Track evaluation progress for streaming updates"""

    def __init__(self):
        self.current_transcript = 0
        self.total_transcripts = 0
        self.current_status = "initializing"
        self.error = None


progress_tracker = {}


async def run_evaluation(evaluation_id: int, db: AsyncSession, transcript_ids: list[int] = None):
    """Run evaluation asynchronously"""
    global progress_tracker

    try:
        # Initialize progress
        progress = EvaluationProgress()
        progress_tracker[evaluation_id] = progress

        # Get evaluation with experiment, judge, and characteristics
        result = await db.execute(
            select(Evaluation).where(Evaluation.id == evaluation_id)
        )
        evaluation = result.scalar_one()

        # Get experiment
        result = await db.execute(
            select(Experiment).where(Experiment.id == evaluation.experiment_id)
        )
        experiment = result.scalar_one()

        # Get judge with characteristics
        result = await db.execute(
            select(Judge).where(Judge.id == evaluation.judge_id)
        )
        judge = result.scalar_one()

        result = await db.execute(
            select(Characteristic).where(Characteristic.judge_id == judge.id)
        )
        characteristics = result.scalars().all()

        if not characteristics:
            raise Exception("Judge has no characteristics defined")

        # Get transcripts (all or filtered by IDs)
        if transcript_ids:
            result = await db.execute(
                select(Transcript).where(Transcript.id.in_(transcript_ids))
            )
        else:
            result = await db.execute(select(Transcript))
        transcripts = result.scalars().all()

        progress.total_transcripts = len(transcripts)
        progress.current_status = "running"

        # Update evaluation status
        evaluation.status = "running"
        await db.commit()

        # Process each transcript
        for idx, transcript in enumerate(transcripts):
            progress.current_transcript = idx + 1
            progress.current_status = f"Processing {transcript.name}"

            try:
                # Step 1: Extract structured data
                extracted_data = await extract_structured_data(
                    experiment.prompt,
                    transcript.content,
                    experiment.schema_json,
                    experiment.model,
                )

                # Step 1.5: Calculate schema stability
                schema_overlap = calculate_schema_overlap(
                    extracted_data,
                    experiment.schema_json
                )

                # Create evaluation result
                eval_result = EvaluationResult(
                    evaluation_id=evaluation_id,
                    transcript_id=transcript.id,
                    extracted_data=extracted_data,
                    schema_overlap_percentage=schema_overlap,
                )
                db.add(eval_result)
                await db.flush()

                # Step 2: Evaluate each characteristic
                votes = []
                for char in characteristics:
                    vote, reasoning, metrics, result_data = await evaluate_characteristic(
                        char.prompt,
                        transcript.content,
                        extracted_data,
                        judge.model,
                        char.schema_json,
                    )

                    char_vote = CharacteristicVote(
                        evaluation_result_id=eval_result.id,
                        characteristic_id=char.id,
                        vote=vote,
                        reasoning=reasoning,
                        metrics=metrics,
                        result_data=result_data,
                    )
                    db.add(char_vote)
                    votes.append(vote)

                # Calculate final score (percentage of passed characteristics)
                final_score = sum(votes) / len(votes) if votes else 0.0
                eval_result.final_score = final_score

                await db.commit()

            except Exception as e:
                print(f"Error evaluating transcript {transcript.name}: {e}")
                # Continue with next transcript
                continue

        # Mark evaluation as completed
        evaluation.status = "completed"
        evaluation.completed_at = datetime.utcnow()
        await db.commit()

        progress.current_status = "completed"

    except Exception as e:
        # Mark evaluation as failed
        result = await db.execute(
            select(Evaluation).where(Evaluation.id == evaluation_id)
        )
        evaluation = result.scalar_one()
        evaluation.status = "failed"
        await db.commit()

        progress.current_status = "failed"
        progress.error = str(e)
        print(f"Evaluation failed: {e}")
