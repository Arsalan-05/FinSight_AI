"""PDF statement ingest — detect bank, extract rows, reconcile balances."""

from __future__ import annotations

from ingest.pdf.detect import detect_bank
from ingest.pdf.extract import extract_statement, extract_with_pdfplumber, extract_with_vision
from ingest.pdf.reconcile import ReconciliationResult, reconcile

__all__ = [
    "ReconciliationResult",
    "detect_bank",
    "extract_statement",
    "extract_with_pdfplumber",
    "extract_with_vision",
    "reconcile",
]
