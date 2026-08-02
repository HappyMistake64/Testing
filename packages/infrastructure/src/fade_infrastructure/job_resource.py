"""Job resource classification for scheduler budgets."""

from __future__ import annotations

import json
from enum import StrEnum

from fade_infrastructure.models import JobModel
from fade_infrastructure.settings import Settings


class JobResourceClass(StrEnum):
    """Scheduler resource class for concurrency limits."""

    LIGHT = "light"
    HEAVY = "heavy"


_LIGHT_JOB_TYPES = frozenset({"noop", "analyze"})


def classify_job(job_type: str, budgets: dict[str, object] | None = None) -> JobResourceClass:
    """Classify a job for concurrent execution budgeting."""
    budgets = budgets or {}
    explicit = budgets.get("resource_class")
    if explicit == JobResourceClass.LIGHT.value:
        return JobResourceClass.LIGHT
    if explicit in {JobResourceClass.HEAVY.value, "medium"}:
        return JobResourceClass.HEAVY
    if job_type in _LIGHT_JOB_TYPES:
        return JobResourceClass.LIGHT
    return JobResourceClass.HEAVY


def classify_job_model(model: JobModel) -> JobResourceClass:
    """Classify a persisted job model."""
    budgets = json.loads(model.budgets_json)
    return classify_job(model.job_type, budgets)


def count_running_by_class(models: list[JobModel]) -> dict[JobResourceClass, int]:
    """Count running jobs grouped by resource class."""
    counts = {JobResourceClass.LIGHT: 0, JobResourceClass.HEAVY: 0}
    for model in models:
        counts[classify_job_model(model)] += 1
    return counts


def can_claim(
    resource_class: JobResourceClass,
    running_counts: dict[JobResourceClass, int],
    settings: Settings,
) -> bool:
    """Return whether another job of the class may be claimed."""
    if resource_class == JobResourceClass.LIGHT:
        return running_counts[JobResourceClass.LIGHT] < settings.max_concurrent_light_jobs
    return running_counts[JobResourceClass.HEAVY] < settings.max_concurrent_heavy_jobs
