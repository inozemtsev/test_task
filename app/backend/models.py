from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(50), default="manual")  # manual or imported
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evaluation_results = relationship("EvaluationResult", back_populates="transcript")
    ground_truths = relationship("GroundTruth", back_populates="transcript", cascade="all, delete-orphan")


class Judge(Base):
    __tablename__ = "judges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    model = Column(String(100), nullable=False)
    judge_config = Column(JSON, nullable=True)  # UI-driven configuration for judge behavior
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evaluations = relationship("Evaluation", back_populates="judge")
    ground_truths = relationship("GroundTruth", back_populates="judge", cascade="all, delete-orphan")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    schema_json = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)
    enable_two_pass = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evaluations = relationship("Evaluation", back_populates="experiment")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    judge_id = Column(Integer, ForeignKey("judges.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    schema_stability = Column(Float, nullable=True)  # Field consistency across transcripts

    experiment = relationship("Experiment", back_populates="evaluations")
    judge = relationship("Judge", back_populates="evaluations")
    results = relationship("EvaluationResult", back_populates="evaluation", cascade="all, delete-orphan")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    transcript_id = Column(Integer, ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False)
    extracted_data = Column(JSON, nullable=True)
    initial_extraction = Column(JSON, nullable=True)  # First pass extraction (two-pass mode)
    review_data = Column(JSON, nullable=True)  # Review findings (two-pass mode)
    final_extraction = Column(JSON, nullable=True)  # Second pass extraction (two-pass mode)
    judge_result = Column(JSON, nullable=True)  # Labeled facts with TP/FP/FN status from judge
    final_score = Column(Float, nullable=True)
    schema_overlap_percentage = Column(Float, nullable=True)
    schema_overlap_data = Column(JSON, nullable=True)  # Jaccard, missing fields, extra fields analysis
    created_at = Column(DateTime, default=datetime.utcnow)

    evaluation = relationship("Evaluation", back_populates="results")
    transcript = relationship("Transcript", back_populates="evaluation_results")


class GroundTruth(Base):
    __tablename__ = "ground_truths"
    __table_args__ = (
        UniqueConstraint("judge_id", "transcript_id", name="uq_ground_truth_judge_transcript"),
    )

    id = Column(Integer, primary_key=True, index=True)
    judge_id = Column(Integer, ForeignKey("judges.id", ondelete="CASCADE"), nullable=False)
    transcript_id = Column(Integer, ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False)
    data = Column(JSON, nullable=False)  # Stored gold facts list
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    judge = relationship("Judge", back_populates="ground_truths")
    transcript = relationship("Transcript", back_populates="ground_truths")
