"""Simple in-process ingest job queue (arq/celery optional later)."""

from __future__ import annotations

import threading
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

# job_id -> status dict
_JOBS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job is not None else None


def list_jobs(*, limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        jobs = list(_JOBS.values())
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return [dict(j) for j in jobs[:limit]]


def enqueue(
    fn: Callable[..., Any],
    *args: Any,
    job_type: str = "ingest",
    **kwargs: Any,
) -> str:
    """Enqueue *fn* to run in a background thread. Returns *job_id*."""
    job_id = str(uuid.uuid4())
    with _LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "job_type": job_type,
            "status": "queued",
            "created_at": _utcnow(),
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
        }

    def _run() -> None:
        with _LOCK:
            job = _JOBS.get(job_id)
            if job is None:
                return
            job["status"] = "running"
            job["started_at"] = _utcnow()
        try:
            result = fn(*args, **kwargs)
            with _LOCK:
                job = _JOBS[job_id]
                job["status"] = "completed"
                job["result"] = result
                job["finished_at"] = _utcnow()
        except Exception as exc:
            with _LOCK:
                job = _JOBS[job_id]
                job["status"] = "failed"
                job["error"] = f"{exc}\n{traceback.format_exc()}"
                job["finished_at"] = _utcnow()

    thread = threading.Thread(target=_run, name=f"ingest-job-{job_id[:8]}", daemon=True)
    thread.start()
    return job_id


def clear_jobs() -> None:
    """Test helper — wipe the in-memory queue."""
    with _LOCK:
        _JOBS.clear()
