from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, JSON
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


class Judge(Base):
    __tablename__ = "judges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    model = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    characteristics = relationship("Characteristic", back_populates="judge", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="judge")


class Characteristic(Base):
    __tablename__ = "characteristics"

    id = Column(Integer, primary_key=True, index=True)
    judge_id = Column(Integer, ForeignKey("judges.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    schema_json = Column(Text, nullable=True)  # Optional structured output schema
    created_at = Column(DateTime, default=datetime.utcnow)

    judge = relationship("Judge", back_populates="characteristics")
    votes = relationship("CharacteristicVote", back_populates="characteristic", cascade="all, delete-orphan")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    schema_json = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)
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

    experiment = relationship("Experiment", back_populates="evaluations")
    judge = relationship("Judge", back_populates="evaluations")
    results = relationship("EvaluationResult", back_populates="evaluation", cascade="all, delete-orphan")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    transcript_id = Column(Integer, ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False)
    extracted_data = Column(JSON, nullable=True)
    final_score = Column(Float, nullable=True)
    schema_overlap_percentage = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    evaluation = relationship("Evaluation", back_populates="results")
    transcript = relationship("Transcript", back_populates="evaluation_results")
    characteristic_votes = relationship("CharacteristicVote", back_populates="result", cascade="all, delete-orphan")


class CharacteristicVote(Base):
    __tablename__ = "characteristic_votes"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_result_id = Column(Integer, ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False)
    characteristic_id = Column(Integer, ForeignKey("characteristics.id", ondelete="CASCADE"), nullable=False)
    vote = Column(Boolean, nullable=False)
    reasoning = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)
    result_data = Column(JSON, nullable=True)  # Full LLM response with all fields
    created_at = Column(DateTime, default=datetime.utcnow)

    result = relationship("EvaluationResult", back_populates="characteristic_votes")
    characteristic = relationship("Characteristic", back_populates="votes")
