"""Unit tests for the RAG pipeline: build_content formatter and retrieve helpers."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from db.models import Transaction
from rag.embedder import build_content
from rag.retriever import retrieve, rrf_fuse

_FAKE_VECTOR = [0.1] * 1024


def _tx(**overrides: object) -> Transaction:
    """Create a transient Transaction (no DB session) for testing."""
    tx = Transaction(
        account_id=overrides.get("account_id", "acc-1"),
        transaction_date=overrides.get("transaction_date", date(2026, 6, 15)),
        description=str(overrides.get("description", "Netflix Premium")),
        amount=float(overrides.get("amount", -15.99)),  # type: ignore[arg-type]
        category=str(overrides.get("category", "Subscriptions")),
        merchant=overrides.get("merchant", "Netflix"),  # type: ignore[arg-type]
        notes=overrides.get("notes", None),  # type: ignore[arg-type]
    )
    # Override auto-generated id if supplied
    if "id" in overrides:
        tx.id = str(overrides["id"])
    return tx


# ── build_content ─────────────────────────────────────────────────────────────


class TestBuildContent:
    def test_includes_date(self) -> None:
        assert "2026-06-15" in build_content(_tx())

    def test_includes_description(self) -> None:
        assert "Netflix Premium" in build_content(_tx())

    def test_includes_category(self) -> None:
        assert "Subscriptions" in build_content(_tx())

    def test_includes_amount_digits(self) -> None:
        assert "15.99" in build_content(_tx())

    def test_debit_label_for_negative_amount(self) -> None:
        assert "debit" in build_content(_tx(amount=-50.0))

    def test_credit_label_for_positive_amount(self) -> None:
        assert "credit" in build_content(_tx(amount=3000.0))

    def test_merchant_included_when_present(self) -> None:
        assert "Whole Foods" in build_content(_tx(merchant="Whole Foods"))

    def test_merchant_omitted_when_none(self) -> None:
        assert "Merchant" not in build_content(_tx(merchant=None))

    def test_notes_included_when_present(self) -> None:
        assert "Annual plan" in build_content(_tx(notes="Annual plan"))

    def test_notes_omitted_when_none(self) -> None:
        assert "Notes" not in build_content(_tx(notes=None))

    def test_fields_joined_by_pipe(self) -> None:
        content = build_content(_tx(merchant=None, notes=None))
        assert " | " in content

    def test_absolute_amount_displayed(self) -> None:
        content = build_content(_tx(amount=-99.50))
        assert "-99" not in content
        assert "99.50" in content


# ── rrf_fuse / retrieve ───────────────────────────────────────────────────────


class TestRrfHelper:
    def test_rrf_fuse_basic(self) -> None:
        assert rrf_fuse([["a", "b"], ["b", "c"]], limit=2)[0] in {"a", "b"}


class TestRetrieve:
    def test_returns_matching_transactions(self) -> None:
        tx1 = _tx(id="tx-1")
        tx2 = _tx(id="tx-2", description="Coffee Shop")

        mock_db = MagicMock()
        # vector path: query().join().filter?().order_by().limit().all()
        # keyword path: similar
        # final hydrate: query().filter().all()
        vector_chain = MagicMock()
        vector_chain.join.return_value = vector_chain
        vector_chain.filter.return_value = vector_chain
        vector_chain.order_by.return_value = vector_chain
        vector_chain.limit.return_value = vector_chain
        vector_chain.all.return_value = [tx1, tx2]

        hydrate_chain = MagicMock()
        hydrate_chain.filter.return_value = hydrate_chain
        hydrate_chain.all.return_value = [tx1, tx2]

        # Alternating query results: vector, keyword, hydrate
        mock_db.query.side_effect = [vector_chain, vector_chain, hydrate_chain]

        with (
            patch("rag.retriever.embed_texts", return_value=[_FAKE_VECTOR]),
            patch("rag.retriever._has_tsvector_column", return_value=False),
            patch("rag.retriever.semantic_cache") as mock_cache,
        ):
            mock_cache.get.return_value = None
            results = retrieve("food spending", mock_db, k=2, use_cache=False, use_rerank=False)

        assert len(results) == 2
        assert {r.id for r in results} == {"tx-1", "tx-2"}

    def test_returns_empty_list_when_no_embeddings(self) -> None:
        mock_db = MagicMock()
        empty_chain = MagicMock()
        empty_chain.join.return_value = empty_chain
        empty_chain.filter.return_value = empty_chain
        empty_chain.order_by.return_value = empty_chain
        empty_chain.limit.return_value = empty_chain
        empty_chain.all.return_value = []
        mock_db.query.return_value = empty_chain

        with (
            patch("rag.retriever.embed_texts", return_value=[_FAKE_VECTOR]),
            patch("rag.retriever._has_tsvector_column", return_value=False),
        ):
            results = retrieve("coffee", mock_db, k=5, use_cache=False, use_rerank=False)

        assert results == []

    def test_uses_query_input_type(self) -> None:
        mock_db = MagicMock()
        empty_chain = MagicMock()
        empty_chain.join.return_value = empty_chain
        empty_chain.filter.return_value = empty_chain
        empty_chain.order_by.return_value = empty_chain
        empty_chain.limit.return_value = empty_chain
        empty_chain.all.return_value = []
        mock_db.query.return_value = empty_chain

        with (
            patch("rag.retriever.embed_texts", return_value=[_FAKE_VECTOR]) as mock_embed,
            patch("rag.retriever._has_tsvector_column", return_value=False),
        ):
            retrieve("subscriptions last month", mock_db, k=3, use_cache=False, use_rerank=False)

        # cleaned query may drop "last month"
        assert mock_embed.call_count == 1
        assert mock_embed.call_args.kwargs.get("input_type") == "query"
        assert mock_embed.call_args.kwargs.get("api_key") == ""
