"""Tests for Canadian bank CSV parsing and Interac normalization."""

from __future__ import annotations

from ingest.bank_csv import detect_and_parse_csv
from ingest.interac import normalize_interac_transaction


class TestInteracParser:
    def test_sent_transfer(self):
        desc, cat, merchant, _ = normalize_interac_transaction(
            "INTERAC E-TRANSFER SENT - JOHN SMITH"
        )
        assert "John Smith" in desc or "JOHN SMITH" in desc.upper()
        assert cat == "Transfers"
        assert merchant is not None

    def test_received_transfer(self):
        desc, cat, _, _ = normalize_interac_transaction("INTERAC E-TRANSFER RECEIVED - MOM")
        assert "MOM" in desc.upper()
        assert cat == "Income"

    def test_non_interac_unchanged(self):
        desc, cat, _, _ = normalize_interac_transaction("Loblaws Groceries", category="Groceries")
        assert desc == "Loblaws Groceries"
        assert cat == "Groceries"


class TestBankCsv:
    def test_generic_format(self):
        csv_text = "date,description,amount,category\n2026-01-15,Coffee,-5.50,Dining\n"
        bank, rows, errors = detect_and_parse_csv(csv_text)
        assert bank in ("finsight", "generic")
        assert len(rows) == 1
        assert errors == []
        assert rows[0]["amount"] == -5.50

    def test_td_withdrawal_deposit(self):
        csv_text = (
            "Date,Description,Withdrawals,Deposits\n"
            "2026-01-10,Grocery Store,45.00,\n"
            "2026-01-01,Salary,,2800.00\n"
        )
        bank, rows, errors = detect_and_parse_csv(csv_text)
        assert bank == "td"
        assert len(rows) == 2
        assert rows[0]["amount"] == -45.0
        assert rows[1]["amount"] == 2800.0

    def test_rbc_format(self):
        csv_text = (
            "Transaction Date,Description 1,Description 2,CAD$\n"
            "2026-02-01,POS LOBLAWS,#123,-52.30\n"
        )
        bank, rows, errors = detect_and_parse_csv(csv_text)
        assert bank == "rbc"
        assert len(rows) == 1
        assert rows[0]["amount"] == -52.30
