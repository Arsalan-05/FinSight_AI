"""Tests for semantic search indexing helpers."""

from __future__ import annotations

from datetime import date
from unittest.mock import PropertyMock, patch

from app.config import settings
from db.models import Account, Transaction, TransactionEmbedding, User
from rag.indexing import (
    count_indexed_transactions,
    index_missing_batch,
    index_transaction_batch,
    reindex_transactions,
)


def _seed_user_with_tx(db_session) -> tuple[str, list[Transaction]]:
    user = User(email="search@test.com", name="Search User")
    db_session.add(user)
    db_session.flush()
    account = Account(
        user_id=user.id,
        name="Checking",
        institution="Test",
        account_type="checking",
    )
    db_session.add(account)
    db_session.flush()
    tx = Transaction(
        account_id=account.id,
        transaction_date=date(2026, 5, 1),
        description="Starbucks coffee",
        amount=-5.50,
        category="Dining",
        merchant="Starbucks",
    )
    db_session.add(tx)
    db_session.commit()
    return account.id, [tx]


class TestSearchIndexing:
    def test_count_indexed_transactions(self, db_session) -> None:
        account_id, txs = _seed_user_with_tx(db_session)
        assert count_indexed_transactions(db_session, [account_id]) == 0
        db_session.add(
            TransactionEmbedding(
                transaction_id=txs[0].id,
                content="coffee",
                embedding=[0.0] * 1024,
            )
        )
        db_session.commit()
        assert count_indexed_transactions(db_session, [account_id]) == 1

    @patch("rag.indexing.embed_texts", return_value=[[0.1] * 1024])
    @patch("rag.indexing.embeddings_runtime_available", return_value=True)
    @patch.object(
        type(settings),
        "embeddings_configured",
        new_callable=PropertyMock,
        return_value=True,
    )
    def test_index_missing_batch(
        self,
        _configured: object,
        _available: object,
        _embed: object,
        db_session,
    ) -> None:
        account_id, _txs = _seed_user_with_tx(db_session)
        indexed, total, indexed_total, remaining = index_missing_batch(
            db_session, [account_id], batch_size=24
        )
        assert indexed == 1
        assert total == 1
        assert indexed_total == 1
        assert remaining == 0

    @patch("rag.indexing.embed_texts", return_value=[[0.1] * 1024])
    @patch("rag.indexing.embeddings_runtime_available", return_value=True)
    @patch.object(
        type(settings),
        "embeddings_configured",
        new_callable=PropertyMock,
        return_value=True,
    )
    def test_reindex_transactions(
        self,
        _configured: object,
        _available: object,
        _embed: object,
        db_session,
    ) -> None:
        account_id, txs = _seed_user_with_tx(db_session)
        indexed = reindex_transactions(db_session, txs)
        assert indexed == 1
        assert count_indexed_transactions(db_session, [account_id]) == 1

    @patch("rag.indexing.embed_texts", return_value=[[0.1] * 1024])
    @patch("rag.indexing.embeddings_runtime_available", return_value=True)
    @patch.object(
        type(settings),
        "embeddings_configured",
        new_callable=PropertyMock,
        return_value=True,
    )
    def test_index_transaction_batch(
        self,
        _configured: object,
        _available: object,
        _embed: object,
        db_session,
    ) -> None:
        account_id, txs = _seed_user_with_tx(db_session)
        indexed = index_transaction_batch(db_session, txs)
        assert indexed == 1
        assert count_indexed_transactions(db_session, [account_id]) == 1
