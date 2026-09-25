"""CSV formula-injection sanitization for export paths."""

from __future__ import annotations

# Characters that make spreadsheet apps treat a cell as a formula
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def sanitize_csv_cell(value: object) -> str:
    """Neutralize formula injection when a string may be opened in Excel/Sheets.

    Prepends a single quote when the value starts with a formula trigger.
    Non-strings are stringified; ``None`` becomes empty string.
    """
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    if not text:
        return text
    if text[0] in _FORMULA_PREFIXES:
        return "'" + text
    return text
