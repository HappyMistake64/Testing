"""Project analysis package."""

from fade_project_analysis.analyzer import AnalysisResult, analyze_project
from fade_project_analysis.ignore_engine import IgnoreEngine

__all__ = ["AnalysisResult", "IgnoreEngine", "analyze_project"]
