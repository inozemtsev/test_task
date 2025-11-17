from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Transcript
from config import settings


async def load_transcripts_from_folder(db: AsyncSession):
    """Load transcripts from the transcripts folder into the database"""
    transcripts_path = settings.transcripts_path

    if not transcripts_path.exists():
        print(f"Transcripts path does not exist: {transcripts_path}")
        return

    # Get existing transcript names
    result = await db.execute(
        select(Transcript.name).where(Transcript.source == "imported")
    )
    existing_names = {row[0] for row in result}

    # Load new transcripts
    loaded_count = 0
    for file_path in transcripts_path.glob("*.txt"):
        if file_path.stem not in existing_names:
            try:
                content = file_path.read_text(encoding="utf-8")
                transcript = Transcript(
                    name=file_path.stem, content=content, source="imported"
                )
                db.add(transcript)
                loaded_count += 1
                print(f"Loaded transcript: {file_path.stem}")
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    if loaded_count > 0:
        await db.commit()
        print(f"Loaded {loaded_count} new transcripts")
