from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Transcript
from schemas import TranscriptCreate, TranscriptResponse

router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])


@router.get("", response_model=list[TranscriptResponse])
async def list_transcripts(db: AsyncSession = Depends(get_db)):
    """List all transcripts"""
    result = await db.execute(select(Transcript).order_by(Transcript.created_at.desc()))
    transcripts = result.scalars().all()
    return transcripts


@router.get("/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(transcript_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific transcript by ID"""
    result = await db.execute(select(Transcript).where(Transcript.id == transcript_id))
    transcript = result.scalar_one_or_none()

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    return transcript


@router.post("", response_model=TranscriptResponse)
async def create_transcript(
    transcript_data: TranscriptCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new transcript"""
    transcript = Transcript(
        name=transcript_data.name, content=transcript_data.content, source="manual"
    )
    db.add(transcript)
    await db.commit()
    await db.refresh(transcript)
    return transcript


@router.delete("/{transcript_id}")
async def delete_transcript(transcript_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a transcript"""
    result = await db.execute(select(Transcript).where(Transcript.id == transcript_id))
    transcript = result.scalar_one_or_none()

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    await db.delete(transcript)
    await db.commit()
    return {"message": "Transcript deleted successfully"}
