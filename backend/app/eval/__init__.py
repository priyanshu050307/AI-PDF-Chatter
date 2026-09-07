"""Unified AI Evaluation Package for AI PDF Chatter."""

from app.eval.datasets import get_dataset, list_datasets
from app.eval.metrics import calculate_run_metrics, check_quality_gates
from app.eval.runner import EvaluationRunner

__all__ = [
    "get_dataset",
    "list_datasets",
    "calculate_run_metrics",
    "check_quality_gates",
    "EvaluationRunner",
]
