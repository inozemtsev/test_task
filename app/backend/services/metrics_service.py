"""
Metrics Service - Pure metric computation from JudgeResult

This module computes precision, recall, F1, and other metrics from labeled facts.
NO LLM calls are made here - all metrics are computed in code.
"""

from typing import Dict, Any
from schemas import JudgeResult, ComputedMetrics, LabeledFact


def compute_metrics(judge_result: JudgeResult) -> ComputedMetrics:
    """
    Compute all metrics from a JudgeResult.

    Args:
        judge_result: JudgeResult with labeled gold_facts and predicted_facts

    Returns:
        ComputedMetrics with precision, recall, F1, counts, etc.
    """
    # Count TP/FP/FN from labeled facts
    tp_count = _count_status(judge_result.gold_facts, "TP")
    fp_count = _count_status(judge_result.predicted_facts, "FP")
    fn_count = _count_status(judge_result.gold_facts, "FN")

    # Compute precision and recall
    precision = compute_precision(tp_count, fp_count)
    recall = compute_recall(tp_count, fn_count)

    # Compute F1 score
    f1 = compute_f1(precision, recall)

    # Hallucination rate and coverage
    hallucination_rate = 1.0 - precision
    coverage = recall  # Coverage is same as recall

    return ComputedMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        tp_count=tp_count,
        fp_count=fp_count,
        fn_count=fn_count,
        hallucination_rate=hallucination_rate,
        coverage=coverage
    )


def compute_precision(tp_count: int, fp_count: int) -> float:
    """
    Compute precision = TP / (TP + FP)

    Precision measures how many of the predicted facts are correct.

    Args:
        tp_count: Number of true positives
        fp_count: Number of false positives

    Returns:
        Precision value between 0.0 and 1.0
    """
    denominator = tp_count + fp_count
    if denominator == 0:
        return 0.0
    return tp_count / denominator


def compute_recall(tp_count: int, fn_count: int) -> float:
    """
    Compute recall = TP / (TP + FN)

    Recall measures how many of the expected facts were found.

    Args:
        tp_count: Number of true positives
        fn_count: Number of false negatives

    Returns:
        Recall value between 0.0 and 1.0
    """
    denominator = tp_count + fn_count
    if denominator == 0:
        return 0.0
    return tp_count / denominator


def compute_f1(precision: float, recall: float) -> float:
    """
    Compute F1 score = 2 * (precision * recall) / (precision + recall)

    F1 is the harmonic mean of precision and recall.

    Args:
        precision: Precision value
        recall: Recall value

    Returns:
        F1 score between 0.0 and 1.0
    """
    denominator = precision + recall
    if denominator == 0:
        return 0.0
    return 2 * (precision * recall) / denominator


def compute_confusion_matrix(judge_result: JudgeResult) -> Dict[str, int]:
    """
    Compute confusion matrix counts from JudgeResult.

    Args:
        judge_result: JudgeResult with labeled facts

    Returns:
        Dictionary with TP, FP, FN, TN counts
    """
    tp_count = _count_status(judge_result.predicted_facts, "TP")
    fp_count = _count_status(judge_result.predicted_facts, "FP")
    fn_count = _count_status(judge_result.gold_facts, "FN")

    # TN (true negatives) not applicable in fact extraction context
    # (we don't have "correctly not extracted" facts)
    tn_count = 0

    return {
        "TP": tp_count,
        "FP": fp_count,
        "FN": fn_count,
        "TN": tn_count
    }


def compute_metrics_by_type(judge_result: JudgeResult) -> Dict[str, ComputedMetrics]:
    """
    Compute metrics broken down by fact type (assets, debts, etc.)

    Args:
        judge_result: JudgeResult with labeled facts

    Returns:
        Dictionary mapping fact_type to ComputedMetrics
    """
    # Group facts by type
    fact_types = set()
    for fact in judge_result.gold_facts + judge_result.predicted_facts:
        if fact.in_scope:
            fact_types.add(fact.fact_type)

    # Compute metrics for each type
    metrics_by_type = {}
    for fact_type in fact_types:
        # Filter facts for this type
        type_gold = [f for f in judge_result.gold_facts if f.fact_type == fact_type and f.in_scope]
        type_predicted = [f for f in judge_result.predicted_facts if f.fact_type == fact_type and f.in_scope]

        # Create a JudgeResult for just this type
        type_judge_result = JudgeResult(
            gold_facts=type_gold,
            predicted_facts=type_predicted
        )

        # Compute metrics
        metrics_by_type[fact_type] = compute_metrics(type_judge_result)

    return metrics_by_type


def _count_status(facts: list[LabeledFact], status: str) -> int:
    """
    Count facts with a specific status. For hallucination tracking we count
    false positives even when they were out of scope so users still see
    hallucinated predictions they didn't ask for.

    Args:
        facts: List of labeled facts
        status: Status to count ("TP", "FP", or "FN")

    Returns:
        Count of facts with that status that are in scope
    """
    return sum(
        1
        for fact in facts
        if fact.status == status and (fact.in_scope or status == "FP")
    )


def aggregate_metrics(metrics_list: list[ComputedMetrics]) -> ComputedMetrics:
    """
    Aggregate metrics across multiple evaluations.

    Sums TP/FP/FN counts and recomputes precision/recall/F1.

    Args:
        metrics_list: List of ComputedMetrics to aggregate

    Returns:
        Aggregated ComputedMetrics
    """
    if not metrics_list:
        return ComputedMetrics(
            precision=0.0,
            recall=0.0,
            f1=0.0,
            tp_count=0,
            fp_count=0,
            fn_count=0,
            hallucination_rate=1.0,
            coverage=0.0
        )

    # Sum counts
    total_tp = sum(m.tp_count for m in metrics_list)
    total_fp = sum(m.fp_count for m in metrics_list)
    total_fn = sum(m.fn_count for m in metrics_list)

    # Recompute metrics from aggregated counts
    precision = compute_precision(total_tp, total_fp)
    recall = compute_recall(total_tp, total_fn)
    f1 = compute_f1(precision, recall)

    return ComputedMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        tp_count=total_tp,
        fp_count=total_fp,
        fn_count=total_fn,
        hallucination_rate=1.0 - precision,
        coverage=recall
    )
