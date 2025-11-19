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


# Judge Config Schema
class JudgeConfig(BaseModel):
    """Configuration for judge behavior - UI-driven settings"""
    entity_types: list[str] = []  # Fact types in scope: ["assets", "debts", "income", etc.]
    profile_name: str = "custom"  # "strict", "lenient", or "custom"
    numeric_tolerance_percent: float = 0.0  # ±X% tolerance for numeric comparisons
    date_granularity: str = "day"  # "day", "month", or "year"
    case_insensitive_strings: bool = False  # Case-insensitive string matching
    ignore_minor_wording_diffs: bool = False  # Ignore minor wording differences
    require_all_fields_match: bool = False  # All fields must match exactly
    required_key_fields: list[str] = []  # Fields that must match
    allow_partial_matches: bool = True  # Allow partial matches to count as correct
    extra_instructions: Optional[str] = None  # Optional advanced notes


# Judge Schemas
class JudgeBase(BaseModel):
    name: str
    model: str
    judge_config: Optional[JudgeConfig] = None


class JudgeCreate(JudgeBase):
    pass


class JudgeUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    judge_config: Optional[JudgeConfig] = None


class JudgeResponse(JudgeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Experiment Schemas
class ExperimentBase(BaseModel):
    name: str
    prompt: str
    schema_json: str = Field(alias="schema_json")
    model: str
    enable_two_pass: bool = False

    class Config:
        populate_by_name = True


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    schema_json: Optional[str] = Field(None, alias="schema_json")
    model: Optional[str] = None
    enable_two_pass: Optional[bool] = None

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


class EvaluationResultResponse(BaseModel):
    id: int
    transcript_id: int
    transcript_name: str
    extracted_data: Any
    initial_extraction: Optional[Any] = None  # First pass (two-pass mode)
    review_data: Optional[dict[str, Any]] = None  # Review findings (two-pass mode)
    final_extraction: Optional[Any] = None  # Second pass (two-pass mode)
    judge_result: Optional[dict[str, Any]] = None  # Labeled facts with TP/FP/FN status
    final_score: Optional[float]
    schema_overlap_data: Optional[dict[str, Any]] = None  # Jaccard similarity and field analysis

    class Config:
        from_attributes = True


class EvaluationResponse(BaseModel):
    id: int
    experiment_id: int
    judge_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    schema_stability: Optional[float] = None
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
    schema_stability: Optional[float] = None  # Field consistency across transcripts
    # Global metrics (aggregated across all transcripts)
    global_precision: Optional[float] = None
    global_recall: Optional[float] = None
    global_f1: Optional[float] = None
    total_tp: Optional[int] = None
    total_fp: Optional[int] = None
    total_fn: Optional[int] = None


class SchemaValidationRequest(BaseModel):
    schema_content: str = Field(alias="schema")

    class Config:
        populate_by_name = True


class SchemaValidationResponse(BaseModel):
    valid: bool
    error: Optional[str] = None


# Judge Result Schemas
class LabeledFact(BaseModel):
    """Individual fact with TP/FP/FN label from judge"""
    id: str  # Unique identifier for this fact
    fact_type: str  # Type of fact: "asset", "debt", "income", etc.
    description: str  # Very detailed description of the fact's data with all attributes and values
    in_scope: bool  # Whether this fact type is in scope for evaluation
    matched_ids: list[str] = []  # IDs of matching facts from the other set
    status: str  # "TP" (true positive), "FP" (false positive), or "FN" (false negative)


class JudgeResult(BaseModel):
    """Complete judge output with labeled facts"""
    gold_facts: list[LabeledFact]  # Facts derived from transcript (expected)
    predicted_facts: list[LabeledFact]  # Facts extracted by the model
    notes: Optional[str] = None  # Optional notes from judge


class ComputedMetrics(BaseModel):
    """Metrics computed in code from JudgeResult (not by LLM)"""
    precision: float  # TP / (TP + FP)
    recall: float  # TP / (TP + FN)
    f1: float  # 2 * (precision * recall) / (precision + recall)
    tp_count: int  # True positives
    fp_count: int  # False positives
    fn_count: int  # False negatives
    hallucination_rate: float  # 1 - precision
    coverage: float  # Same as recall


class GroundTruthGenerateRequest(BaseModel):
    transcript_ids: Optional[list[int]] = None


class GroundTruthUpdateRequest(BaseModel):
    ground_truth: Any


class GroundTruthDetailResponse(BaseModel):
    transcript: TranscriptResponse
    ground_truth: Optional[Any] = None
    updated_at: Optional[datetime] = None
