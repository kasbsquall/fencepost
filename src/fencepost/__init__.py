"""Fencepost stages 1-4: attribute, select, mutate, and execute."""

from .models import AnalysisResult, RunConfig
from .pipeline import run_analysis

__all__ = ["AnalysisResult", "RunConfig", "run_analysis"]
