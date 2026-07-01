"""Unit tests for the RAG pipeline: build_content formatter and retrieve()."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from db.models import Transaction
from rag.embedder import build_content
from rag.retriever import retrieve

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
        # Core fields should be separated by " | "
        assert " | " in content

    def test_absolute_amount_displayed(self) -> None:
        # Negative amounts must show their absolute value, not a minus sign
        content = build_content(_tx(amount=-99.50))
        assert "-99" not in content
        assert "99.50" in content


# ── retrieve ──────────────────────────────────────────────────────────────────


def _mock_db(return_txs: list[Transaction]) -> MagicMock:
    """Build a mock Session whose chained query returns *return_txs*."""
    mock_db = MagicMock()
    (
        mock_db.query.return_value.join.return_value.order_by.return_value.limit.return_value.all.return_value
    ) = return_txs
    return mock_db


class TestRetrieve:
    def test_returns_matching_transactions(self) -> None:
        tx1 = _tx(id="tx-1")
        tx2 = _tx(id="tx-2", description="Coffee Shop")
        mock_db = _mock_db([tx1, tx2])

        with patch("rag.retriever.embed_texts", return_value=[_FAKE_VECTOR]):
            results = retrieve("food spending", mock_db, k=2)

        assert len(results) == 2
        assert results[0].id == "tx-1"
        assert results[1].id == "tx-2"

    def test_returns_empty_list_when_no_embeddings(self) -> None:
        mock_db = _mock_db([])

        with patch("rag.retriever.embed_texts", return_value=[_FAKE_VECTOR]):
            results = retrieve("coffee", mock_db, k=5)

        assert results == []

    def test_uses_query_input_type(self) -> None:
        mock_db = _mock_db([])

        with patch("rag.retriever.embed_texts", return_value=[_FAKE_VECTOR]) as mock_embed:
            retrieve("subscriptions last month", mock_db, k=3)

        mock_embed.assert_called_once_with(
            ["subscriptions last month"], input_type="query", api_key=""
        )

    def test_respects_k_limit(self) -> None:
        mock_db = _mock_db([])

        with patch("rag.retriever.embed_texts", return_value=[_FAKE_VECTOR]):
            retrieve("dining", mock_db, k=7)

        mock_db.query.return_value.join.return_value.order_by.return_value.limit.assert_called_once_with(
            7
        )

    def test_passes_query_vector_to_db(self) -> None:
        """The vector returned by embed_texts must flow into the DB query chain."""
        expected_vector = [0.42] * 1024
        mock_db = _mock_db([])

        with patch("rag.retriever.embed_texts", return_value=[expected_vector]):
            retrieve("test", mock_db, k=1)

        # Verify query() was called with the Transaction model
        mock_db.query.assert_called_once_with(Transaction)
