#!/usr/bin/env python3
"""Regenerate docs/metrics.json from a real test run and the offline eval set.

Usage (from the repo root):  backend/.venv/bin/python scripts/generate_metrics.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
METRICS_PATH = ROOT / "docs" / "metrics.json"


def _git_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT)
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _pytest_counts() -> dict[str, int]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    counts = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|skipped|errors?)", tail)}
    return {"passed": counts.get("passed", 0), "failed": counts.get("failed", 0)}


def _line_count(path: Path) -> int:
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def _eval(subset: str) -> dict[str, float]:
    sys.path.insert(0, str(BACKEND))
    from evals.run import run_eval

    s = run_eval(model="dry-run", subset=subset, dry_run=True)
    retrieval = s.get("retrieval") or {}
    return {
        "questions": s["n_questions"],
        "answer_accuracy": s["answer_numeric_acc"],
        "tool_selection_exact": s["tool_exact_acc"],
        "hallucinated_number_rate": s["hallucinated_number_rate"],
        "refusal_accuracy": s["refusal_acc"],
        "recall_at_5": retrieval.get("recall@5"),
        "ndcg_at_10": retrieval.get("ndcg@10"),
    }


def main() -> None:
    version = tomllib.loads((BACKEND / "pyproject.toml").read_text())["project"]["version"]
    evals_dir = BACKEND / "evals"
    metrics = {
        "version": version,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit_sha": _git_sha(),
        "tests": {"backend": _pytest_counts()},
        "evals": {
            "golden_questions": _line_count(evals_dir / "golden.jsonl"),
            "smoke_questions": _line_count(evals_dir / "smoke.jsonl"),
            "retrieval_queries": _line_count(evals_dir / "retrieval.jsonl"),
            "mode": "offline dry run: fixture ground truth scored through the production guardrail",
            "smoke": _eval("smoke"),
            "full": _eval("full"),
        },
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"Wrote {METRICS_PATH}")


if __name__ == "__main__":
    main()
