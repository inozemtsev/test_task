from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any


# Transcript Schemas
class TranscriptBase(BaseModel):
    name: str
    content: str


class TranscriptCreate(TranscriptBase):
    pass


class TranscriptResponse(TranscriptBase):
    id: int
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Characteristic Schemas
class CharacteristicBase(BaseModel):
    name: str
    prompt: str
    schema_json: Optional[str] = None


class CharacteristicCreate(CharacteristicBase):
    pass


class CharacteristicResponse(CharacteristicBase):
    id: int
    judge_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Judge Schemas
class JudgeBase(BaseModel):
    name: str
    model: str


class JudgeCreate(JudgeBase):
    pass


class JudgeUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None


class JudgeResponse(JudgeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    characteristics: list[CharacteristicResponse] = []

    class Config:
        from_attributes = True


# Experiment Schemas
class ExperimentBase(BaseModel):
    name: str
    prompt: str
    schema_json: str = Field(alias="schema_json")
    model: str

    class Config:
        populate_by_name = True


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    schema_json: Optional[str] = Field(None, alias="schema_json")
    model: Optional[str] = None

    class Config:
        populate_by_name = True


class ExperimentResponse(ExperimentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Evaluation Schemas
class EvaluationRunRequest(BaseModel):
    experiment_id: int
    judge_id: int
    transcript_ids: Optional[list[int]] = None  # If None, run on all transcripts


class CharacteristicVoteResponse(BaseModel):
    id: int
    characteristic_id: int
    characteristic_name: str
    vote: bool
    reasoning: Optional[str]
    metrics: Optional[dict[str, Any]] = None  # Can be float or {numerator, denominator}
    result_data: Optional[dict[str, Any]] = None  # Full LLM response with all fields

    class Config:
        from_attributes = True


class EvaluationResultResponse(BaseModel):
    id: int
    transcript_id: int
    transcript_name: str
    extracted_data: Any
    final_score: Optional[float]
    schema_overlap_percentage: Optional[float] = None
    characteristic_votes: list[CharacteristicVoteResponse] = []

    class Config:
        from_attributes = True


class EvaluationResponse(BaseModel):
    id: int
    experiment_id: int
    judge_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    results: list[EvaluationResultResponse] = []

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    experiment_id: int
    experiment_name: str
    avg_score: float
    num_transcripts: int
    evaluation_id: int
    completed_at: datetime
    avg_schema_overlap: Optional[float] = None
    avg_metrics: Optional[dict[str, Any]] = None  # Can be float or {numerator, denominator}
    characteristic_results: Optional[dict[str, Any]] = None  # Per-characteristic aggregated results


class SchemaValidationRequest(BaseModel):
    schema_content: str = Field(alias="schema")

    class Config:
        populate_by_name = True


class SchemaValidationResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
