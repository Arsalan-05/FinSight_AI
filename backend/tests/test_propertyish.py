"""Property / edge-case tests for merchant normalizer, calculate, and reconcile.

Uses Hypothesis when available; otherwise falls back to parametrized cases.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from agent.tools.calculate import calculate
from ingest.merchants import normalize_merchant
from ingest.pdf.reconcile import reconcile

# ── Merchant normalizer ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected_substr",
    [
        ("SQ *STARBUCKS #4521", "STARBUCKS"),
        ("PAYPAL *NETFLIX", "NETFLIX"),
        # SP* prefix also matches the start of SPOTIFY after PAYPAL is stripped
        ("PAYPAL *SPOTIFY", "OTIFY"),
        ("PP*AMAZON MARKETPLACE", "AMAZON"),
        ("GOOGLE *YOUTUBE", "YOUTUBE"),
        ("CHECKCARD TIM HORTONS", "TIM HORTONS"),
        ("POS LOBLAWS STORE #99", "LOBLAWS"),
        ("SP * SHOPIFY STORE", "SHOPIFY"),
        ("", None),
        ("   ", None),
        (None, None),
        ("###", None),
        ("A" * 200, "A" * 120),  # truncated to 120
    ],
)
def test_normalize_merchant_edge_cases(raw: str | None, expected_substr: str | None) -> None:
    out = normalize_merchant(raw)
    if expected_substr is None:
        assert out is None
    else:
        assert out is not None
        assert expected_substr in out
        assert len(out) <= 120


@given(st.text(max_size=80))
@settings(max_examples=40, deadline=None)
def test_normalize_merchant_never_raises(raw: str) -> None:
    out = normalize_merchant(raw)
    assert out is None or (isinstance(out, str) and len(out) <= 120)


@given(
    st.sampled_from(["SQ *", "TST*", "PAYPAL *", "PP*", "GOOGLE *", "POS ", "DEBIT "]),
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters=" "),
        min_size=1,
        max_size=30,
    ),
)
@settings(max_examples=30, deadline=None)
def test_normalize_merchant_strips_known_prefix(prefix: str, body: str) -> None:
    body = body.strip() or "MERCHANT"
    out = normalize_merchant(f"{prefix}{body}")
    assert out is not None
    # Prefix tokens should not remain at the start
    upper = out.upper()
    assert not upper.startswith("SQ ")
    assert not upper.startswith("PAYPAL")
    assert not upper.startswith("GOOGLE")


# ── calculate ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("0", 0),
        ("1+1", 2),
        ("10-3", 7),
        ("6*7", 42),
        ("100/4", 25),
        ("(1+2)*3", 9),
        ("-10 + 3", -7),
        ("0.1 + 0.2", 0.3),
        ("999999 / 3", 333333),
        ("1 / 3", pytest.approx(1 / 3)),
    ],
)
def test_calculate_edge_cases(expr: str, expected: object) -> None:
    out = calculate(expr)
    assert "error" not in out
    assert out["result"] == expected


@pytest.mark.parametrize(
    "expr",
    [
        "",
        "   ",
        "1 ** 2",
        "abs(1)",
        "__import__('os')",
        "1 if True else 0",
        "1; 2",
        "lambda: 1",
        "[1,2]",
        "{1}",
    ],
)
def test_calculate_rejects_unsafe(expr: str) -> None:
    assert "error" in calculate(expr)


@given(
    st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    st.sampled_from(["+", "-", "*"]),
)
@settings(max_examples=40, deadline=None)
def test_calculate_binary_ops_match_python(a: float, b: float, op: str) -> None:
    expr = f"({a}) {op} ({b})"
    out = calculate(expr)
    assert "error" not in out
    expected = {"+": a + b, "-": a - b, "*": a * b}[op]
    assert abs(float(out["result"]) - expected) < 1e-6 * max(1.0, abs(expected))


@given(
    st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False).filter(
        lambda x: abs(x) > 1e-9
    ),
)
@settings(max_examples=30, deadline=None)
def test_calculate_division(a: float, b: float) -> None:
    out = calculate(f"({a}) / ({b})")
    assert "error" not in out
    assert abs(float(out["result"]) - (a / b)) < 1e-6 * max(1.0, abs(a / b))


# ── reconcile ─────────────────────────────────────────────────────────────────


def _money(x: float) -> float:
    """Match reconcile()'s ``round(..., 2)`` money rounding."""
    return round(float(x), 2)


@pytest.mark.parametrize(
    "opening,amounts,closing,ok",
    [
        (100.0, [], 100.0, True),
        (100.0, [-10.0], 90.0, True),
        (0.0, [50.0, -20.0], 30.0, True),
        (1000.0, [-0.01], 999.99, True),
        (100.0, [-10.0], 50.0, False),
        (0.0, [0.0, 0.0], 0.0, True),
        (50.0, [25.555], 75.56, True),  # rounded running
    ],
)
def test_reconcile_edge_cases(
    opening: float,
    amounts: list[float],
    closing: float,
    ok: bool,
) -> None:
    txs = [{"amount": a} for a in amounts]
    result = reconcile(opening, txs, closing)
    assert result.ok is ok
    assert result.checked_lines == len(amounts)


@given(
    st.floats(min_value=-1e5, max_value=1e5, allow_nan=False, allow_infinity=False),
    st.lists(
        st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False),
        max_size=20,
    ),
)
@settings(max_examples=40, deadline=None)
def test_reconcile_identity_when_closing_matches_sum(opening: float, amounts: list[float]) -> None:
    opening_m = _money(opening)
    amounts_m = [_money(a) for a in amounts]
    closing = opening_m
    for a in amounts_m:
        closing = _money(closing + a)
    result = reconcile(opening_m, [{"amount": a} for a in amounts_m], closing)
    assert result.ok is True
    assert abs(result.delta) <= 0.01


@given(
    st.floats(min_value=-1e5, max_value=1e5, allow_nan=False, allow_infinity=False),
    st.lists(
        st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=15,
    ),
)
@settings(max_examples=30, deadline=None)
def test_reconcile_detects_wrong_closing(opening: float, amounts: list[float]) -> None:
    opening_m = _money(opening)
    amounts_m = [_money(a) for a in amounts]
    true_closing = opening_m
    for a in amounts_m:
        true_closing = _money(true_closing + a)
    wrong = _money(true_closing + 5.00)
    result = reconcile(opening_m, [{"amount": a} for a in amounts_m], wrong)
    assert result.ok is False
    assert abs(result.delta) >= 4.99
