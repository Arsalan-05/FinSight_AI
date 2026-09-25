"""Tests for merchant normalization, PDF reconcile, filters, RRF, and dedupe."""

from __future__ import annotations

from datetime import date

from agent.graph import MAX_TOOL_LOOPS, validate_tool_args
from ingest.dedupe import find_duplicates, match_score
from ingest.jobs import clear_jobs, enqueue, get_job
from ingest.merchants import normalize_merchant
from ingest.pdf.detect import detect_bank
from ingest.pdf.extract import extract_with_pdfplumber
from ingest.pdf.reconcile import reconcile
from rag.filters import parse_query_filters
from rag.retriever import rrf_fuse


class TestNormalizeMerchant:
    def test_strips_square_prefix(self) -> None:
        assert normalize_merchant("SQ *COFFEE SHOP") == "COFFEE SHOP"

    def test_strips_tst_prefix(self) -> None:
        assert normalize_merchant("TST*BURGER PLACE") == "BURGER PLACE"

    def test_strips_paypal(self) -> None:
        assert normalize_merchant("PAYPAL *NETFLIX") == "NETFLIX"

    def test_strips_store_number(self) -> None:
        assert normalize_merchant("LOBLAWS #1234") == "LOBLAWS"

    def test_strips_city_province(self) -> None:
        cleaned = normalize_merchant("TIM HORTONS TORONTO ON")
        assert cleaned is not None
        assert "TORONTO" not in cleaned.upper()
        assert "ON" not in cleaned.split()

    def test_empty_returns_none(self) -> None:
        assert normalize_merchant("   ") is None
        assert normalize_merchant(None) is None


class TestPdfDetectAndReconcile:
    def test_detect_rbc(self) -> None:
        assert detect_bank("Royal Bank of Canada Account Statement") == "rbc"

    def test_detect_td(self) -> None:
        assert detect_bank("TD Canada Trust Everyday Checking") == "td"

    def test_reconcile_success_rbc_synthetic(self) -> None:
        statement = {
            "bank": "rbc",
            "opening": 1000.00,
            "closing": 912.50,
            "transactions": [
                {
                    "date": date(2026, 1, 2),
                    "description": "POS LOBLAWS",
                    "amount": -52.30,
                    "balance": 947.70,
                },
                {
                    "date": date(2026, 1, 5),
                    "description": "PAYROLL DEPOSIT",
                    "amount": 200.00,
                    "balance": 1147.70,
                },
                {
                    "date": date(2026, 1, 8),
                    "description": "RENT INTERAC",
                    "amount": -235.20,
                    "balance": 912.50,
                },
            ],
        }
        result = reconcile(
            statement["opening"],
            statement["transactions"],
            statement["closing"],
        )
        assert result.ok is True
        assert result.delta == 0.0
        assert result.line_errors == []

    def test_reconcile_success_td_synthetic(self) -> None:
        statement = {
            "bank": "td",
            "opening": 500.00,
            "closing": 455.00,
            "transactions": [
                {"date": date(2026, 2, 1), "description": "GROCERY", "amount": -45.00},
            ],
        }
        result = reconcile(
            statement["opening"],
            statement["transactions"],
            statement["closing"],
        )
        assert result.ok is True
        assert result.computed_closing == 455.00

    def test_reconcile_detects_mismatch(self) -> None:
        result = reconcile(100.0, [{"amount": -10.0}], 50.0)
        assert result.ok is False
        assert abs(result.delta - 40.0) < 0.01

    def test_extract_text_statement_and_reconcile(self) -> None:
        text = """
        RBC Royal Bank Statement
        Opening Balance: 1000.00
        2026-01-03 POS LOBLAWS TORONTO -52.30
        2026-01-10 PAYROLL ACME 500.00
        Closing Balance: 1447.70
        """
        extracted = extract_with_pdfplumber(text)
        assert extracted["bank"] == "rbc"
        assert len(extracted["transactions"]) >= 2
        result = reconcile(
            extracted["opening"],
            extracted["transactions"],
            extracted["closing"],
        )
        assert result.ok is True


class TestQueryFilters:
    def test_parses_last_month(self) -> None:
        f = parse_query_filters("coffee last month", today=date(2026, 3, 15))
        assert f.date_from == date(2026, 2, 1)
        assert f.date_to == date(2026, 2, 28)
        assert "last month" not in f.cleaned_query.lower()

    def test_parses_amount_over(self) -> None:
        f = parse_query_filters("purchases over $50 at Costco")
        assert f.amount_min == 50.0
        assert "costco" in f.cleaned_query.lower()

    def test_parses_dollar_exact(self) -> None:
        f = parse_query_filters("find the $15.99 netflix charge")
        assert f.amount_exact == 15.99

    def test_parses_iso_range(self) -> None:
        f = parse_query_filters("groceries 2026-01-01 2026-01-31")
        assert f.date_from == date(2026, 1, 1)
        assert f.date_to == date(2026, 1, 31)


class TestRrfFuse:
    def test_prefers_items_in_both_lists(self) -> None:
        fused = rrf_fuse([["a", "b", "c"], ["c", "a", "d"]], limit=3)
        assert fused[0] == "a" or fused[0] == "c"
        assert set(fused[:2]) == {"a", "c"}

    def test_preserves_unique_order(self) -> None:
        fused = rrf_fuse([["x", "y"], ["z"]], k=60)
        assert fused == ["x", "y", "z"] or fused[0] == "x"

    def test_empty_lists(self) -> None:
        assert rrf_fuse([[], []]) == []


class TestDedupe:
    def test_matches_across_sources(self) -> None:
        plaid = [
            {
                "id": "p1",
                "date": date(2026, 1, 10),
                "amount": -45.00,
                "merchant": "Loblaws",
            }
        ]
        csv_rows = [
            {
                "id": "c1",
                "date": date(2026, 1, 11),
                "amount": -45.00,
                "merchant": "POS LOBLAWS #99",
            }
        ]
        matches = find_duplicates(plaid, csv_rows)
        assert len(matches) == 1
        assert matches[0].left_id == "p1"
        assert matches[0].right_id == "c1"

    def test_rejects_different_amount(self) -> None:
        scored = match_score(
            {"date": date(2026, 1, 10), "amount": -45.0, "merchant": "Loblaws"},
            {"date": date(2026, 1, 10), "amount": -50.0, "merchant": "Loblaws"},
        )
        assert scored is None

    def test_rejects_outside_date_window(self) -> None:
        scored = match_score(
            {"date": date(2026, 1, 1), "amount": -10.0, "merchant": "Uber"},
            {"date": date(2026, 1, 10), "amount": -10.0, "merchant": "Uber"},
        )
        assert scored is None


class TestJobsAndToolValidation:
    def test_enqueue_completes(self) -> None:
        clear_jobs()

        def work() -> dict[str, int]:
            return {"ok": 1}

        job_id = enqueue(work, job_type="test")
        # Poll briefly
        import time

        for _ in range(50):
            job = get_job(job_id)
            assert job is not None
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.02)
        job = get_job(job_id)
        assert job is not None
        assert job["status"] == "completed"
        assert job["result"] == {"ok": 1}

    def test_validate_tool_args(self) -> None:
        assert MAX_TOOL_LOOPS == 6
        ok, _ = validate_tool_args("search_transactions", {"query": "coffee", "k": 5})
        assert ok is True
        ok, err = validate_tool_args("search_transactions", {})
        assert ok is False
        assert "query" in err
