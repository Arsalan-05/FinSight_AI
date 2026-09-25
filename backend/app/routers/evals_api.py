"""Eval run history from on-disk ``evals/results/*.json`` (no DB required)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/evals", tags=["evals"])

_RESULTS_DIR = Path(__file__).resolve().parents[2] / "evals" / "results"

# Keys safe / useful to surface in the listing (omit huge per-question payloads)
_SUMMARY_KEYS = (
    "model",
    "subset",
    "dry_run",
    "timestamp",
    "n_questions",
    "answer_numeric_acc",
    "tool_exact_acc",
    "tool_partial_acc",
    "hallucinated_number_rate",
    "refusal_acc",
    "retrieval",
    "fixture_transaction_count",
    "planted_leak_count",
)


def _summarize(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"id": path.stem, "file": path.name}
    for key in _SUMMARY_KEYS:
        if key in payload:
            summary[key] = payload[key]
    return summary


@router.get("")
@router.get("/")
def list_evals(
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """List recent eval result files (newest first by filename / mtime)."""
    if not _RESULTS_DIR.is_dir():
        return []

    files = sorted(
        _RESULTS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]

    out: list[dict[str, Any]] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        out.append(_summarize(path, payload))
    return out


@router.get("/{run_id}")
def get_eval(run_id: str) -> dict[str, Any]:
    """Return one eval result summary by filename stem (e.g. ``20260925T161414Z``)."""
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run id")
    path = _RESULTS_DIR / f"{run_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Eval run not found")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Corrupt eval result") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="Corrupt eval result")
    return _summarize(path, payload)
