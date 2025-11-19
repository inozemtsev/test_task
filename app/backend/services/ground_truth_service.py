from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import GroundTruth, Transcript, Judge
from services.llm_service import generate_gold_facts


DEFAULT_JUDGE_CONFIG = {
    "entity_types": [],
    "profile_name": "custom",
    "numeric_tolerance_percent": 0.0,
    "date_granularity": "day",
    "case_insensitive_strings": False,
    "ignore_minor_wording_diffs": False,
    "require_all_fields_match": False,
    "required_key_fields": [],
    "allow_partial_matches": True,
    "extra_instructions": None,
}


def get_effective_judge_config(judge_config: dict | None) -> dict:
    """Return a usable judge configuration with sensible defaults."""
    return judge_config if judge_config else DEFAULT_JUDGE_CONFIG.copy()


async def _upsert_ground_truth(
    db: AsyncSession,
    judge_id: int,
    transcript_id: int,
    data: list[dict],
):
    """Create or update stored ground truth entry."""
    existing_query = await db.execute(
        select(GroundTruth).where(
            GroundTruth.judge_id == judge_id,
            GroundTruth.transcript_id == transcript_id,
        )
    )
    ground_truth = existing_query.scalar_one_or_none()

    if ground_truth:
        ground_truth.data = data
    else:
        ground_truth = GroundTruth(
            judge_id=judge_id,
            transcript_id=transcript_id,
            data=data,
        )
        db.add(ground_truth)

    await db.commit()


async def _generate_and_store_ground_truth(
    db: AsyncSession,
    judge: Judge,
    transcript: Transcript,
    config: dict,
) -> list[dict]:
    """Generate ground truth for a single transcript and persist it."""
    gold_facts = await generate_gold_facts(
        transcript.content,
        config,
        judge.model,
    )
    await _upsert_ground_truth(db, judge.id, transcript.id, gold_facts)
    return gold_facts


async def ensure_ground_truth_for_transcripts(
    db: AsyncSession,
    judge: Judge,
    transcripts: list[Transcript],
    ground_truth_map: dict[int, list[dict]],
):
    """Ensure all transcripts have stored ground truth for this judge."""
    config = get_effective_judge_config(judge.judge_config)
    for transcript in transcripts:
        if transcript.id in ground_truth_map:
            continue

        try:
            gold_facts = await _generate_and_store_ground_truth(
                db, judge, transcript, config
            )
            ground_truth_map[transcript.id] = gold_facts
        except Exception as e:
            await db.rollback()
            raise Exception(
                f"Failed to generate ground truth for transcript '{transcript.name}': {e}"
            )


async def regenerate_ground_truth_for_transcripts(
    db: AsyncSession,
    judge: Judge,
    transcripts: list[Transcript],
):
    """Regenerate (or create) and store ground truth for the provided transcripts."""
    config = get_effective_judge_config(judge.judge_config)
    generated = 0
    failures: list[dict] = []

    for transcript in transcripts:
        try:
            await _generate_and_store_ground_truth(db, judge, transcript, config)
            generated += 1
        except Exception as e:
            await db.rollback()
            failures.append(
                {
                    "transcript_id": transcript.id,
                    "transcript_name": transcript.name,
                    "error": str(e),
                }
            )

    return {
        "generated": generated,
        "total": len(transcripts),
        "failures": failures,
    }
