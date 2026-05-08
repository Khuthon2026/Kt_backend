from typing import Any
from dataclasses import dataclass, field

@dataclass
class Job:
    job_id: str
    status: str = "pending"      # pending | processing | done | failed
    progress: int = 0
    current_step: str = "store_fetch"
    mode: str = "app_only"
    result: dict[str, Any] | None = None
    error: str | None = None


_store: dict[str, Job] = {}


def create_job(job_id: str, mode: str) -> Job:
    job = Job(job_id=job_id, mode=mode)
    _store[job_id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _store.get(job_id)


def update_job(job_id: str, **kwargs: Any) -> None:
    job = _store.get(job_id)
    if job is None:
        return
    for key, value in kwargs.items():
        setattr(job, key, value)
