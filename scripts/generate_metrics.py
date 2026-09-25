#!/usr/bin/env python3
"""Generate docs/metrics.json from local pytest collection and optional coverage.

CI should run this after tests and commit or upload the artifact.
Hardcoded counts in README/docs must be replaced by reading this file.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "docs" / "metrics.json"
BACKEND = ROOT / "backend"


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=ROOT,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _collect_pytest() -> int:
    try:
        out = subprocess.check_output(
            ["uv", "run", "pytest", "--collect-only", "-q"],
            cwd=BACKEND,
            stderr=subprocess.STDOUT,
        ).decode()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"pytest collect failed: {exc}", file=sys.stderr)
        return 0
    for line in out.splitlines():
        # e.g. "120 tests collected in 0.06s"
        if "tests collected" in line:
            return int(line.split()[0])
    return 0


def _count_golden() -> int:
    path = BACKEND / "evals" / "golden.jsonl"
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def _count_retrieval() -> int:
    path = BACKEND / "evals" / "retrieval.jsonl"
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def main() -> None:
    existing: dict = {}
    if METRICS_PATH.exists():
        existing = json.loads(METRICS_PATH.read_text())

    collected = _collect_pytest()
    metrics = {
        "version": existing.get("version", "2.0.0-dev"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit_sha": _git_sha(),
        "tests": {
            **existing.get("tests", {}),
            "backend_collected": collected,
            "e2e_checkpoints": existing.get("tests", {}).get("e2e_checkpoints", 20),
        },
        "evals": {
            **existing.get("evals", {}),
            "golden_questions": _count_golden() or existing.get("evals", {}).get("golden_questions", 0),
            "retrieval_queries": _count_retrieval()
            or existing.get("evals", {}).get("retrieval_queries", 0),
            "smoke_subset": existing.get("evals", {}).get("smoke_subset", 30),
            "baseline": existing.get("evals", {}).get("baseline", {}),
        },
        "leaks": existing.get("leaks", {}),
        "performance": existing.get("performance", {}),
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"Wrote {METRICS_PATH} (tests={collected})")


if __name__ == "__main__":
    main()
