"""CLI: ``python -m evals.run --model groq-8b --subset smoke|full``.

Offline ``--dry-run`` scores fixture ground-truth helpers without an LLM.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.fixtures.seed_persona import (
    GYM_FEE,
    NETFLIX_NEW,
    NETFLIX_OLD,
    RENT_CAD,
    SPOTIFY_NEW,
    SPOTIFY_OLD,
    build_fixture_transactions,
    summarize_fixture,
)
from evals.metrics import (
    hallucinated_number_rate,
    mean,
    mrr,
    ndcg_at_k,
    numeric_match,
    recall_at_k,
    refusal_accuracy,
    tool_selection_accuracy,
)

EVALS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVALS_DIR / "results"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _category_spend(transactions: list[dict[str, Any]], category: str) -> float:
    total = 0.0
    for t in transactions:
        if t["category"].lower() == category.lower() and float(t["amount"]) < 0:
            total += abs(float(t["amount"]))
    return round(total, 2)


def _merchant_spend(transactions: list[dict[str, Any]], merchant: str) -> float:
    total = 0.0
    for t in transactions:
        if (t.get("merchant") or "").lower() == merchant.lower() and float(t["amount"]) < 0:
            total += abs(float(t["amount"]))
    return round(total, 2)


def _dry_run_answer(
    case: dict[str, Any],
    *,
    transactions: list[dict[str, Any]],
    planted_leaks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Deterministic ground-truth helper answers (no LLM)."""
    category = case.get("category", "")
    expected = case.get("expected_answer") or {}
    expected_tools = list(case.get("expected_tools") or [])
    qid = case.get("id", "")
    question = (case.get("question") or "").lower()

    if category in ("refusal", "adversarial"):
        answer = (
            "I can only help with your personal finances in FinSight. "
            "I will not follow instructions embedded in transaction descriptions "
            "or jailbreak / exfiltration requests."
        )
        # Adversarial lookup prompts may still call search; refusal prompts use no tools.
        tools_used = list(expected_tools)
        tool_json = (
            [json.dumps({"results": [], "refused_injection": True})]
            if tools_used
            else ["{}"]
        )
        return {
            "answer": answer,
            "tools_used": tools_used,
            "tool_json": tool_json,
            "numeric": None,
            "did_refuse": True,
            "should_refuse": True,
        }

    # Insights / planted leaks
    if "nsf" in question:
        numeric = 48.0
        answer = f"There is an NSF fee of ${numeric:.2f}."
        tools_used = expected_tools or ["get_financial_insights"]
        tool_json = [json.dumps({"fees": [{"type": "nsf", "amount": numeric}]})]
    elif "atm" in question and "fee" in question:
        numeric = 7.0  # 2 × 3.50
        answer = f"ATM fees total ${numeric:.2f} across the year."
        tools_used = expected_tools or ["get_financial_insights"]
        tool_json = [json.dumps({"fees": [{"type": "atm", "amount": 3.5, "count": 2}]})]
    elif "duplicate" in question or "charged twice" in question:
        numeric = 87.43
        answer = f"Possible duplicate Best Buy charges of ${numeric:.2f} within 48 hours."
        tools_used = expected_tools or ["get_financial_insights", "search_transactions"]
        tool_json = [json.dumps({"duplicate": {"merchant": "Best Buy", "amount": numeric}})]
    elif "goodlife" in question or "gym" in question and "forgotten" in question:
        numeric = round(GYM_FEE * 12, 2)
        answer = f"GoodLife Fitness membership costs ${GYM_FEE:.2f}/mo (${numeric:.2f}/yr)."
        tools_used = expected_tools or ["get_financial_insights", "aggregate_spending"]
        tool_json = [json.dumps({"merchant": "GoodLife Fitness", "monthly": GYM_FEE, "yearly": numeric})]
    elif "spotify" in question and ("increase" in question or "price" in question):
        numeric = round(SPOTIFY_NEW - SPOTIFY_OLD, 2)
        answer = (
            f"Spotify rose from ${SPOTIFY_OLD:.2f} to ${SPOTIFY_NEW:.2f} "
            f"(+${numeric:.2f}) mid-year."
        )
        tools_used = expected_tools or ["get_financial_insights", "aggregate_spending"]
        tool_json = [
            json.dumps(
                {
                    "spotify_old": SPOTIFY_OLD,
                    "spotify_new": SPOTIFY_NEW,
                    "delta": numeric,
                }
            )
        ]
    elif "netflix" in question and ("increase" in question or "price" in question):
        numeric = round(NETFLIX_NEW - NETFLIX_OLD, 2)
        answer = (
            f"Netflix rose from ${NETFLIX_OLD:.2f} to ${NETFLIX_NEW:.2f} "
            f"(+${numeric:.2f}) mid-year."
        )
        tools_used = expected_tools or ["get_financial_insights", "aggregate_spending"]
        tool_json = [
            json.dumps(
                {
                    "netflix_old": NETFLIX_OLD,
                    "netflix_new": NETFLIX_NEW,
                    "delta": numeric,
                }
            )
        ]
    elif "rent" in question:
        numeric = RENT_CAD
        answer = f"Monthly rent via Interac is ${numeric:.2f}."
        tools_used = expected_tools or ["aggregate_spending", "search_transactions"]
        tool_json = [json.dumps({"rent": numeric, "total": numeric})]
    elif "groceries" in question or "grocery" in question:
        if "june" in question or "jun" in question:
            june = [
                t
                for t in transactions
                if t["category"] == "Groceries"
                and t["transaction_date"].month == 6
                and float(t["amount"]) < 0
            ]
            numeric = round(sum(abs(float(t["amount"])) for t in june), 2)
        else:
            numeric = _category_spend(transactions, "Groceries")
        answer = f"Grocery spending totals ${numeric:.2f}."
        tools_used = expected_tools or ["aggregate_spending"]
        tool_json = [json.dumps({"category": "Groceries", "total": -numeric, "total_abs": numeric})]
    elif "dining" in question or "restaurants" in question or "tim hortons" in question:
        if "tim hortons" in question:
            numeric = _merchant_spend(transactions, "Tim Hortons")
            answer = f"Tim Hortons spending totals ${numeric:.2f}."
            tool_json = [json.dumps({"merchant": "Tim Hortons", "total": -numeric})]
        else:
            numeric = _category_spend(transactions, "Dining")
            answer = f"Dining spending totals ${numeric:.2f}."
            tool_json = [json.dumps({"category": "Dining", "total": -numeric})]
        tools_used = expected_tools or ["aggregate_spending"]
    elif "amazon" in question:
        numeric = _merchant_spend(transactions, "Amazon")
        answer = f"Amazon spending totals ${numeric:.2f} CAD (includes USD FX purchases)."
        tools_used = expected_tools or ["aggregate_spending", "search_transactions"]
        tool_json = [json.dumps({"merchant": "Amazon", "total": -numeric})]
    else:
        # Fall back to expected_answer numeric / contains scaffolding
        numeric = expected.get("numeric")
        contains = expected.get("contains") or []
        if numeric is not None:
            answer = f"The total is ${float(numeric):.2f}."
            tool_json = [json.dumps({"total": float(numeric)})]
        elif contains:
            answer = " ".join(str(c) for c in contains)
            tool_json = [json.dumps({"contains": contains})]
            numeric = None
        else:
            summary = summarize_fixture(transactions, planted_leaks)
            answer = (
                f"Fixture has {summary['transaction_count']} transactions "
                f"from {summary['date_start']} to {summary['date_end']}."
            )
            tool_json = [json.dumps(summary)]
            numeric = None
        tools_used = expected_tools or ["aggregate_spending"]

    # Prefer golden expected numeric when present (scores the harness wiring)
    if expected.get("numeric") is not None and expected.get("total") is None:
        # keep computed numeric; if golden has numeric use it for "perfect" dry-run
        pass
    if expected.get("numeric") is not None:
        # Dry-run claims the expected ground truth to validate metric plumbing
        numeric = float(expected["numeric"])
        answer = f"The total is ${numeric:.2f}."
        tool_json = [json.dumps({"total": numeric, "amount": numeric})]

    return {
        "answer": answer,
        "tools_used": tools_used,
        "tool_json": tool_json,
        "numeric": numeric,
        "did_refuse": False,
        "should_refuse": False,
        "case_id": qid,
    }


def _score_case(
    case: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    expected = case.get("expected_answer") or {}
    tol = float(expected.get("tolerance") if expected.get("tolerance") is not None else 0.01)
    tools = tool_selection_accuracy(result.get("tools_used"), case.get("expected_tools"))
    hall = hallucinated_number_rate(result.get("answer") or "", result.get("tool_json") or [])

    num_ok: bool | None = None
    if expected.get("numeric") is not None:
        num_ok = numeric_match(result.get("numeric"), expected["numeric"], tolerance=tol)

    contains = expected.get("contains") or []
    contains_ok = True
    answer_l = (result.get("answer") or "").lower()
    for needle in contains:
        if str(needle).lower() not in answer_l:
            contains_ok = False
            break

    refuse_ok = refusal_accuracy(
        should_refuse=bool(result.get("should_refuse")),
        did_refuse=bool(result.get("did_refuse")),
    )

    return {
        "id": case.get("id"),
        "category": case.get("category"),
        "numeric_match": num_ok,
        "contains_ok": contains_ok if contains else None,
        "tool_exact": tools["exact"],
        "tool_partial": tools["partial"],
        "hallucinated_number_rate": hall["rate"],
        "refusal_ok": refuse_ok,
        "answer": result.get("answer"),
        "tools_used": result.get("tools_used"),
    }


def _score_retrieval(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Dry-run retrieval: use relevant_ids as perfect ranking when resolvable."""
    recalls5: list[float] = []
    recalls10: list[float] = []
    mrrs: list[float] = []
    ndcgs: list[float] = []
    for row in rows:
        relevant = [r for r in (row.get("relevant_ids") or []) if r != "will_resolve_at_runtime"]
        # Placeholder IDs → treat as unresolved; score 0 unless dry-run synthesizes
        if not relevant:
            # Synthetic: pretend first "placeholder" slot ranks at position 1 with 1 relevant
            relevant = ["synthetic-relevant"]
            ranked = ["synthetic-relevant"] + [f"noise-{i}" for i in range(9)]
        else:
            ranked = list(relevant) + [f"noise-{i}" for i in range(10)]
        recalls5.append(recall_at_k(relevant, ranked, 5))
        recalls10.append(recall_at_k(relevant, ranked, 10))
        mrrs.append(mrr(relevant, ranked))
        ndcgs.append(ndcg_at_k(relevant, ranked, 10))
    return {
        "recall@5": mean(recalls5),
        "recall@10": mean(recalls10),
        "mrr": mean(mrrs),
        "ndcg@10": mean(ndcgs),
    }


def _print_summary(summary: dict[str, Any]) -> None:
    rows = [
        ("subset", summary.get("subset")),
        ("model", summary.get("model")),
        ("dry_run", summary.get("dry_run")),
        ("questions", summary.get("n_questions")),
        ("answer_numeric_acc", f"{summary.get('answer_numeric_acc', 0):.3f}"),
        ("tool_exact_acc", f"{summary.get('tool_exact_acc', 0):.3f}"),
        ("tool_partial_acc", f"{summary.get('tool_partial_acc', 0):.3f}"),
        ("halluc_$rate", f"{summary.get('hallucinated_number_rate', 0):.3f}"),
        ("refusal_acc", f"{summary.get('refusal_acc', 0):.3f}"),
        ("recall@5", f"{summary.get('retrieval', {}).get('recall@5', 0):.3f}"),
        ("ndcg@10", f"{summary.get('retrieval', {}).get('ndcg@10', 0):.3f}"),
        ("fixture_txs", summary.get("fixture_transaction_count")),
        ("planted_leaks", summary.get("planted_leak_count")),
    ]
    width = max(len(str(k)) for k, _ in rows)
    print()
    print("=== FinSight eval summary ===")
    for key, val in rows:
        print(f"  {key:<{width}}  {val}")
    print()


def run_eval(
    *,
    model: str,
    subset: str,
    dry_run: bool,
) -> dict[str, Any]:
    golden_path = EVALS_DIR / "golden.jsonl"
    smoke_path = EVALS_DIR / "smoke.jsonl"
    retrieval_path = EVALS_DIR / "retrieval.jsonl"

    if subset == "smoke":
        cases = _load_jsonl(smoke_path)
    else:
        cases = _load_jsonl(golden_path)

    # Deterministic fixture (no DB required for dry-run)
    fake_accounts = {
        "rbc_checking": "00000000-0000-4000-8000-000000000001",
        "td_credit": "00000000-0000-4000-8000-000000000002",
    }
    transactions, planted_leaks = build_fixture_transactions(
        "00000000-0000-4000-8000-0000000000aa",
        fake_accounts,
    )
    fixture_summary = summarize_fixture(transactions, planted_leaks)

    if not dry_run:
        # Live LLM path reserved for later phases; Phase 1 ships dry-run first.
        print(
            "Live LLM eval is not wired in Phase 1 — falling back to --dry-run helpers.",
            file=sys.stderr,
        )
        dry_run = True

    scored: list[dict[str, Any]] = []
    for case in cases:
        result = _dry_run_answer(
            case,
            transactions=transactions,
            planted_leaks=planted_leaks,
        )
        scored.append(_score_case(case, result))

    numeric_cases = [s for s in scored if s["numeric_match"] is not None]
    refuse_cases = [
        s for s in scored if s.get("category") in ("refusal", "adversarial")
    ]
    retrieval_rows = _load_jsonl(retrieval_path) if retrieval_path.exists() else []
    retrieval_scores = _score_retrieval(retrieval_rows)

    summary: dict[str, Any] = {
        "model": model,
        "subset": subset,
        "dry_run": dry_run,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_questions": len(scored),
        "answer_numeric_acc": mean(
            [1.0 if s["numeric_match"] else 0.0 for s in numeric_cases]
        )
        if numeric_cases
        else 0.0,
        "tool_exact_acc": mean([1.0 if s["tool_exact"] else 0.0 for s in scored]),
        "tool_partial_acc": mean([float(s["tool_partial"]) for s in scored]),
        "hallucinated_number_rate": mean(
            [float(s["hallucinated_number_rate"]) for s in scored]
        ),
        "refusal_acc": mean([1.0 if s["refusal_ok"] else 0.0 for s in refuse_cases])
        if refuse_cases
        else 1.0,
        "retrieval": retrieval_scores,
        "fixture_transaction_count": fixture_summary["transaction_count"],
        "planted_leak_count": fixture_summary["planted_leak_count"],
        "fixture": fixture_summary,
        "cases": scored,
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FinSight AI Phase 1 eval runner")
    parser.add_argument(
        "--model",
        default="groq-8b",
        help="Model id label for the results file (default: groq-8b)",
    )
    parser.add_argument(
        "--subset",
        choices=("smoke", "full"),
        default="smoke",
        help="smoke = smoke.jsonl; full = golden.jsonl",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Score fixture ground-truth helpers without calling an LLM",
    )
    args = parser.parse_args(argv)

    summary = run_eval(model=args.model, subset=args.subset, dry_run=args.dry_run)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"{stamp}.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    _print_summary(summary)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
