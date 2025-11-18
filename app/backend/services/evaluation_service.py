from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import AsyncSessionLocal
from models import (
    Evaluation,
    EvaluationResult,
    CharacteristicVote,
    Transcript,
    Experiment,
    Judge,
    Characteristic,
)
from services.llm_service import extract_structured_data, evaluate_characteristic, calculate_schema_stability, review_extraction, extract_with_review
from datetime import datetime
import asyncio
from concurrent.futures import ProcessPoolExecutor
import os


class EvaluationProgress:
    """Track evaluation progress for streaming updates"""

    def __init__(self):
        self.current_transcript = 0
        self.total_transcripts = 0
        self.current_status = "initializing"
        self.error = None


progress_tracker = {}


async def _async_process_transcript(
    transcript_id: int,
    transcript_name: str,
    transcript_content: str,
    experiment_prompt: str,
    experiment_schema: str,
    experiment_model: str,
    enable_two_pass: bool,
    judge_model: str,
    characteristics: list[dict],  # [{id, prompt, schema_json}, ...]
):
    """Process a single transcript: extraction and characteristic evaluations

    This function does NOT write to the database - it only processes data
    and returns results for the main process to write.
    """
    try:
        # Step 1: Extract structured data (first pass)
        extracted_data = await extract_structured_data(
            experiment_prompt,
            transcript_content,
            experiment_schema,
            experiment_model,
        )

        # Two-pass extraction flow
        initial_extraction = None
        review_data = None
        final_extraction = None

        if enable_two_pass:
            initial_extraction = extracted_data

            review_data = await review_extraction(
                transcript_content,
                initial_extraction,
                experiment_schema,
                experiment_model
            )

            final_extraction = await extract_with_review(
                experiment_prompt,
                transcript_content,
                experiment_schema,
                initial_extraction,
                review_data,
                experiment_model
            )

            extracted_data = final_extraction

        # Calculate schema overlap analysis
        from services.schema_utils import calculate_field_overlap
        schema_overlap_data = calculate_field_overlap(extracted_data, experiment_schema)

        # Step 2: Evaluate each characteristic
        votes = []
        characteristic_votes = []

        for char in characteristics:
            vote, reasoning, metrics, result_data = await evaluate_characteristic(
                char['prompt'],
                transcript_content,
                extracted_data,
                judge_model,
                char['schema_json'],
            )

            characteristic_votes.append({
                'characteristic_id': char['id'],
                'vote': vote,
                'reasoning': reasoning,
                'metrics': metrics,
                'result_data': result_data,
            })
            votes.append(vote)

        # Calculate final score
        final_score = sum(votes) / len(votes) if votes else 0.0

        return {
            'transcript_id': transcript_id,
            'transcript_name': transcript_name,
            'extracted_data': extracted_data,
            'initial_extraction': initial_extraction,
            'review_data': review_data,
            'final_extraction': final_extraction,
            'schema_overlap_data': schema_overlap_data,
            'characteristic_votes': characteristic_votes,
            'final_score': final_score,
            'success': True,
            'error': None,
        }

    except Exception as e:
        print(f"Error processing transcript {transcript_name}: {e}")
        return {
            'transcript_id': transcript_id,
            'transcript_name': transcript_name,
            'success': False,
            'error': str(e),
        }


def process_transcript_worker(
    transcript_id: int,
    transcript_name: str,
    transcript_content: str,
    experiment_prompt: str,
    experiment_schema: str,
    experiment_model: str,
    enable_two_pass: bool,
    judge_model: str,
    characteristics: list[dict],
):
    """Sync wrapper that runs async processing in a new event loop

    This is the entry point called by ProcessPoolExecutor workers.
    """
    # Create a new event loop for this process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            _async_process_transcript(
                transcript_id,
                transcript_name,
                transcript_content,
                experiment_prompt,
                experiment_schema,
                experiment_model,
                enable_two_pass,
                judge_model,
                characteristics,
            )
        )
        return result
    finally:
        loop.close()


async def run_evaluation(evaluation_id: int, transcript_ids: list[int] = None):
    """Run evaluation asynchronously with parallel transcript processing"""
    global progress_tracker

    # Create own database session for background task
    async with AsyncSessionLocal() as db:
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

            # Serialize characteristics for workers
            characteristics_data = [
                {
                    'id': char.id,
                    'prompt': char.prompt,
                    'schema_json': char.schema_json,
                }
                for char in characteristics
            ]

            # Process transcripts in parallel using ProcessPoolExecutor
            max_workers = min(os.cpu_count() or 1, len(transcripts))
            loop = asyncio.get_event_loop()

            # Collect all results first, then write to DB
            all_results = []

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all transcript jobs
                futures = []
                for transcript in transcripts:
                    future = loop.run_in_executor(
                        executor,
                        process_transcript_worker,
                        transcript.id,
                        transcript.name,
                        transcript.content,
                        experiment.prompt,
                        experiment.schema_json,
                        experiment.model,
                        experiment.enable_two_pass,
                        judge.model,
                        characteristics_data,
                    )
                    futures.append(future)

                # Wait for all results to complete
                completed_count = 0
                for future in asyncio.as_completed(futures):
                    result = await future
                    completed_count += 1

                    # Update progress
                    progress.current_transcript = completed_count
                    if result['success']:
                        progress.current_status = f"Completed {result['transcript_name']} ({completed_count}/{len(transcripts)})"
                        all_results.append(result)
                    else:
                        progress.current_status = f"Failed {result['transcript_name']} ({completed_count}/{len(transcripts)})"
                        print(f"Transcript processing failed: {result['error']}")

            # Now write all results to database (after executor is closed)
            progress.current_status = "Writing results to database..."
            all_extracted_data = []

            for result in all_results:
                try:
                    # Collect extracted data for stability calculation
                    all_extracted_data.append(result['extracted_data'])

                    # Create evaluation result with two-pass artifacts
                    eval_result = EvaluationResult(
                        evaluation_id=evaluation_id,
                        transcript_id=result['transcript_id'],
                        extracted_data=result['extracted_data'],
                        initial_extraction=result['initial_extraction'],
                        review_data=result['review_data'],
                        final_extraction=result['final_extraction'],
                        schema_overlap_data=result.get('schema_overlap_data'),
                        final_score=result['final_score'],
                    )
                    db.add(eval_result)
                    await db.flush()

                    # Add characteristic votes
                    for vote_data in result['characteristic_votes']:
                        char_vote = CharacteristicVote(
                            evaluation_result_id=eval_result.id,
                            characteristic_id=vote_data['characteristic_id'],
                            vote=vote_data['vote'],
                            reasoning=vote_data['reasoning'],
                            metrics=vote_data['metrics'],
                            result_data=vote_data['result_data'],
                        )
                        db.add(char_vote)

                    await db.commit()

                except Exception as e:
                    print(f"Error writing results for transcript {result['transcript_name']}: {e}")
                    await db.rollback()
                    continue

            # Calculate schema stability across all transcripts
            if all_extracted_data:
                schema_stability = calculate_schema_stability(all_extracted_data)
                evaluation.schema_stability = schema_stability
            else:
                evaluation.schema_stability = 0.0

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
