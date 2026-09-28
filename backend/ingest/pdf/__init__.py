"""Statement text ingest: detect the bank, parse rows, reconcile balances."""

from __future__ import annotations

from ingest.pdf.detect import detect_bank
from ingest.pdf.extract import extract_statement_text
from ingest.pdf.reconcile import ReconciliationResult, reconcile

__all__ = [
    "ReconciliationResult",
    "detect_bank",
    "extract_statement_text",
    "reconcile",
]
