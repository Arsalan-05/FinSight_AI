"""Unit tests for Canadian planning engines — hand-computed cases."""

from __future__ import annotations

import json

import pytest

from planning import DISCLAIMER
from planning.forecast import _percentile, run_cash_forecast
from planning.loader import (
    available_years,
    combined_marginal_rate,
    load_rules,
    marginal_rate,
    tax_on_income,
)
from planning.osap import (
    interest_only_first_month,
    monthly_payment,
    payment_formula_terms,
    plan_osap,
)
from planning.registered import _allocate_year, optimize_registered
from planning.scenarios import apply_overlay, what_if
from planning.student_tax import estimate_tuition_credit

# ── Loader / rules ─────────────────────────────────────────────────────────────


def test_disclaimer_constant() -> None:
    assert DISCLAIMER == "Educational estimates, not financial or tax advice."


def test_available_years_includes_2025_2026() -> None:
    years = available_years()
    assert 2025 in years
    assert 2026 in years


def test_load_rules_2026_limits() -> None:
    rules = load_rules(2026)
    assert rules.tfsa_limit == 7000
    assert rules.rrsp_limit == 33810
    assert rules.fhsa_limit == 8000
    assert rules.fhsa_lifetime_cap == 40000
    assert rules.osap.interest_rate == 0.055
    assert rules.osap.standard_amortization_years == 9.5
    assert "tfsa" in rules.sources


def test_load_rules_2025_limits() -> None:
    rules = load_rules(2025)
    assert rules.tfsa_limit == 7000
    assert rules.rrsp_limit == 32490
    assert rules.federal_tax_brackets[0].rate == 0.145


def test_load_rules_missing_year() -> None:
    with pytest.raises(FileNotFoundError):
        load_rules(1999)


def test_marginal_rate_hand_computed_2026() -> None:
    rules = load_rules(2026)
    # First bracket
    assert marginal_rate(10000, rules.federal_tax_brackets) == 0.14
    # Second bracket boundary
    assert marginal_rate(58523, rules.federal_tax_brackets) == 0.14
    assert marginal_rate(58524, rules.federal_tax_brackets) == 0.205
    # Top bracket
    assert marginal_rate(300000, rules.federal_tax_brackets) == 0.33


def test_tax_on_income_hand_computed() -> None:
    rules = load_rules(2026)
    # Income entirely in first federal bracket: 50_000 * 0.14 = 7_000
    assert tax_on_income(50000, rules.federal_tax_brackets) == 7000.0
    # Cross into second: 58_523 * 0.14 + (60_000 - 58_523) * 0.205
    # = 8193.22 + 1477 * 0.205 = 8193.22 + 302.785 = 8496.005 → 8496.01
    expected = round(58523 * 0.14 + (60000 - 58523) * 0.205, 2)
    assert tax_on_income(60000, rules.federal_tax_brackets) == expected


def test_combined_marginal_rate_threshold_boundary() -> None:
    rules = load_rules(2026)
    # 100k: fed 20.5% + ont 9.15% = 29.65% < 30%
    assert combined_marginal_rate(rules, 100000) == pytest.approx(0.2965)
    # 120k: fed 26% + ont 11.16% = 37.16%
    assert combined_marginal_rate(rules, 120000) == pytest.approx(0.3716)


# ── Registered optimizer ───────────────────────────────────────────────────────


def test_allocate_fhsa_first_for_first_time_buyer() -> None:
    """Hand case: $10k budget, FTHB → $8k FHSA then remainder to TFSA (low MTR)."""
    alloc = _allocate_year(
        budget=10000,
        first_time_buyer=True,
        mtr=0.20,
        fhsa_room=8000,
        tfsa_room=7000,
        rrsp_room=5000,
    )
    assert alloc["fhsa"] == 8000
    assert alloc["tfsa"] == 2000
    assert alloc["rrsp"] == 0
    assert alloc["unallocated"] == 0


def test_allocate_prefer_rrsp_when_high_mtr() -> None:
    alloc = _allocate_year(
        budget=5000,
        first_time_buyer=False,
        mtr=0.35,
        fhsa_room=0,
        tfsa_room=7000,
        rrsp_room=10000,
    )
    assert alloc["rrsp"] == 5000
    assert alloc["tfsa"] == 0


def test_allocate_prefer_tfsa_when_low_mtr() -> None:
    alloc = _allocate_year(
        budget=5000,
        first_time_buyer=False,
        mtr=0.20,
        fhsa_room=0,
        tfsa_room=7000,
        rrsp_room=10000,
    )
    assert alloc["tfsa"] == 5000
    assert alloc["rrsp"] == 0


def test_allocate_respects_room_caps_and_unallocated() -> None:
    alloc = _allocate_year(
        budget=20000,
        first_time_buyer=True,
        mtr=0.40,
        fhsa_room=8000,
        tfsa_room=1000,
        rrsp_room=2000,
    )
    assert alloc["fhsa"] == 8000
    assert alloc["rrsp"] == 2000
    assert alloc["tfsa"] == 1000
    assert alloc["unallocated"] == 9000


def test_optimize_single_year_fthb_fills_fhsa() -> None:
    result = optimize_registered(
        income=45000,
        age=22,
        first_time_buyer=True,
        horizon=1,
        annual_contribution=8000,
        tax_year=2026,
        existing_room={"tfsa": 0, "rrsp": 0, "fhsa": 0},
        growth_rate=0.0,
    )
    assert result["disclaimer"] == DISCLAIMER
    assert result["fhsa_eligible"] is True
    assert result["allocation_priority"][0] == "fhsa"
    y0 = result["years"][0]
    assert y0["fhsa"] == 8000
    assert y0["tfsa"] == 0
    assert y0["rrsp"] == 0
    # Tax savings = 8000 * combined MTR(45k)
    # fed 14% + ont 5.05% = 19.05%
    assert y0["marginal_rate"] == pytest.approx(0.1905)
    assert y0["estimated_tax_savings"] == pytest.approx(8000 * 0.1905)


def test_optimize_high_income_prefers_rrsp() -> None:
    result = optimize_registered(
        income=120000,
        age=30,
        first_time_buyer=False,
        horizon=1,
        annual_contribution=10000,
        tax_year=2026,
        existing_room={"tfsa": 0, "rrsp": 0, "fhsa": 0},
        growth_rate=0.0,
    )
    assert result["allocation_priority"] == ["rrsp", "tfsa"]
    y0 = result["years"][0]
    # RRSP room = min(18%*120000, 33810) = min(21600, 33810) = 21600
    assert y0["rrsp"] == 10000
    assert y0["tfsa"] == 0


def test_optimize_low_income_prefers_tfsa() -> None:
    result = optimize_registered(
        income=40000,
        age=25,
        first_time_buyer=False,
        horizon=1,
        annual_contribution=7000,
        tax_year=2026,
        growth_rate=0.0,
    )
    assert result["allocation_priority"] == ["tfsa", "rrsp"]
    assert result["years"][0]["tfsa"] == 7000


def test_optimize_fhsa_lifetime_cap() -> None:
    """Hand case: $8k/yr × 5 yrs hits $40k lifetime; year 6 gets $0 FHSA."""
    result = optimize_registered(
        income=50000,
        age=24,
        first_time_buyer=True,
        horizon=6,
        annual_contribution=8000,
        tax_year=2026,
        existing_room={"fhsa_lifetime_contributed": 0},
        growth_rate=0.0,
    )
    fhsa_years = [y["fhsa"] for y in result["years"]]
    assert fhsa_years[:5] == [8000, 8000, 8000, 8000, 8000]
    assert fhsa_years[5] == 0
    assert result["totals"]["fhsa"] == 40000
    assert result["years"][5]["room_after"]["fhsa_lifetime_remaining"] == 0


def test_optimize_existing_tfsa_room_carry() -> None:
    """With $3k existing TFSA room + $7k annual, $10k budget → all TFSA."""
    result = optimize_registered(
        income=35000,
        age=28,
        first_time_buyer=False,
        horizon=1,
        annual_contribution=10000,
        tax_year=2026,
        existing_room={"tfsa": 3000},
        growth_rate=0.0,
    )
    assert result["years"][0]["tfsa"] == 10000
    assert result["years"][0]["room_after"]["tfsa"] == 0


def test_optimize_growth_compounding_hand() -> None:
    """$1000 TFSA contrib, 10% growth, 2 years, no prior balance.
    Year1 end: 1000. Year2 end: 1000*1.1 + 1000 = 2100.
    """
    result = optimize_registered(
        income=30000,
        age=20,
        first_time_buyer=False,
        horizon=2,
        annual_contribution=1000,
        tax_year=2026,
        growth_rate=0.10,
    )
    assert result["years"][0]["balances"]["tfsa"] == 1000.0
    assert result["years"][1]["balances"]["tfsa"] == 2100.0


def test_optimize_rrsp_room_18_percent_cap() -> None:
    """Income $20k → RRSP annual room = min(3600, 33810) = 3600.
    High MTR forced via... actually low income has low MTR so TFSA first.
    Force RRSP by exhausting TFSA room with existing=0 and budget after TFSA.
    """
    result = optimize_registered(
        income=20000,
        age=40,
        first_time_buyer=False,
        horizon=1,
        annual_contribution=12000,
        tax_year=2026,
        growth_rate=0.0,
    )
    y0 = result["years"][0]
    # Low MTR → TFSA first ($7000), then RRSP capped at 18%*20k = $3600
    assert y0["tfsa"] == 7000
    assert y0["rrsp"] == 3600
    assert y0["unallocated"] == 1400


def test_optimize_rejects_bad_horizon() -> None:
    with pytest.raises(ValueError):
        optimize_registered(
            income=1, age=20, first_time_buyer=False, horizon=0, annual_contribution=0
        )


def test_optimize_age_blocks_fhsa() -> None:
    result = optimize_registered(
        income=50000,
        age=17,
        first_time_buyer=True,
        horizon=1,
        annual_contribution=8000,
        tax_year=2026,
        growth_rate=0.0,
    )
    assert result["fhsa_eligible"] is False
    assert result["years"][0]["fhsa"] == 0


# ── OSAP ───────────────────────────────────────────────────────────────────────


def test_monthly_payment_zero_interest_hand() -> None:
    # $12,000 over 1 year, 0% → $1,000/mo exactly
    assert monthly_payment(12000, 0.0, 1.0) == 1000.0


def test_monthly_payment_formula_hand() -> None:
    """P=10_000, r_annual=12% → monthly r=0.01, n=12.
    payment = 10000 * (0.01 * 1.01^12) / (1.01^12 - 1)
    1.01^12 ≈ 1.12682503013
    = 10000 * 0.0112682503013 / 0.12682503013 ≈ 888.487...
    """
    terms = payment_formula_terms(10000, 0.12, 1.0)
    assert terms["n"] == 12
    assert terms["r"] == pytest.approx(0.01)
    expected = 10000 * (0.01 * (1.01**12)) / ((1.01**12) - 1)
    assert terms["raw_payment"] == pytest.approx(expected)
    assert monthly_payment(10000, 0.12, 1.0) == round(expected, 2)


def test_interest_only_first_month_hand() -> None:
    # $24,000 at 6% → first month interest = 24000 * 0.005 = 120
    assert interest_only_first_month(24000, 0.06) == 120.0


def test_plan_osap_standard_pays_off() -> None:
    plan = plan_osap(
        principal=12000,
        annual_rate=0.0,
        standard_years=1.0,
        accelerated_years=0.5,
        extra_monthly=0,
        tax_year=2026,
    )
    assert plan["disclaimer"] == DISCLAIMER
    assert plan["standard"]["monthly_payment"] == 1000.0
    assert plan["standard"]["months"] == 12
    assert plan["standard"]["total_paid"] == 12000.0
    assert plan["standard"]["total_interest"] == 0.0
    assert plan["accelerated"]["monthly_payment"] == 2000.0
    assert plan["accelerated"]["months"] == 6


def test_plan_osap_extra_payments_reduce_interest() -> None:
    base = plan_osap(
        principal=20000,
        annual_rate=0.06,
        standard_years=5.0,
        accelerated_years=3.0,
        extra_monthly=0,
        tax_year=2026,
    )
    extra = plan_osap(
        principal=20000,
        annual_rate=0.06,
        standard_years=5.0,
        accelerated_years=3.0,
        extra_monthly=100,
        tax_year=2026,
    )
    assert extra["with_extra_payments"]["months"] < base["standard"]["months"]
    assert (
        extra["with_extra_payments"]["total_interest"]
        < base["standard"]["total_interest"]
    )
    assert extra["with_extra_payments"]["interest_saved_vs_standard"] > 0


def test_plan_osap_accelerated_saves_interest() -> None:
    plan = plan_osap(
        principal=15000,
        annual_rate=0.055,
        standard_years=9.5,
        accelerated_years=5.0,
        tax_year=2026,
    )
    assert plan["accelerated"]["total_interest"] < plan["standard"]["total_interest"]
    assert plan["accelerated"]["interest_saved_vs_standard"] > 0
    assert plan["accelerated"]["months"] < plan["standard"]["months"]


def test_plan_osap_first_month_interest_matches() -> None:
    principal = 18000.0
    rate = 0.06
    plan = plan_osap(
        principal=principal,
        annual_rate=rate,
        standard_years=2.0,
        tax_year=2026,
    )
    head = plan["standard"]["schedule_head"]
    assert head[0]["interest"] == interest_only_first_month(principal, rate)


def test_plan_osap_rejects_negative_principal() -> None:
    with pytest.raises(ValueError):
        plan_osap(principal=-1, tax_year=2026)


def test_plan_osap_uses_yaml_defaults() -> None:
    plan = plan_osap(principal=1000, tax_year=2026)
    assert plan["annual_interest_rate"] == 0.055
    assert plan["standard_years"] == 9.5


# ── Student tax ────────────────────────────────────────────────────────────────


def test_tuition_credit_ontario_hand() -> None:
    # $10,000 tuition × 5.05% = $505 (Ontario lowest rate)
    result = estimate_tuition_credit(
        eligible_tuition=10000, province="ontario", tax_year=2026
    )
    assert "ESTIMATE" in result["label"]
    assert result["federal_credit_estimate"] == 0.0
    assert result["provincial_credit_rate"] == 0.0505
    assert result["provincial_credit_estimate"] == 505.0
    assert result["total_credit_estimate"] == 505.0
    assert result["disclaimer"] == DISCLAIMER


def test_tuition_credit_unsupported_province() -> None:
    result = estimate_tuition_credit(eligible_tuition=5000, province="bc")
    assert result["supported"] is False
    assert result["total_credit_estimate"] == 0.0


# ── Forecast ───────────────────────────────────────────────────────────────────


def test_percentile_hand() -> None:
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _percentile(vals, 0) == 1.0
    assert _percentile(vals, 100) == 5.0
    assert _percentile(vals, 50) == 3.0


def test_forecast_deterministic_zero_variance() -> None:
    """Start 1000, +500 income, -300 expense × 12 months → end = 1000 + 12*200 = 3400."""
    result = run_cash_forecast(
        starting_balance=1000,
        monthly_income_mean=500,
        monthly_income_std=0,
        monthly_expense_mean=300,
        monthly_expense_std=0,
        months=12,
        n_sims=50,
        seed=42,
    )
    assert result["disclaimer"] == DISCLAIMER
    assert result["ending_balance"]["p10"] == 3400.0
    assert result["ending_balance"]["p50"] == 3400.0
    assert result["ending_balance"]["p90"] == 3400.0
    assert result["p_ruin"] == 0.0


def test_forecast_seed_reproducible() -> None:
    a = run_cash_forecast(
        starting_balance=500,
        monthly_income_mean=2000,
        monthly_income_std=400,
        monthly_expense_mean=1800,
        monthly_expense_std=300,
        months=6,
        n_sims=200,
        seed=7,
    )
    b = run_cash_forecast(
        starting_balance=500,
        monthly_income_mean=2000,
        monthly_income_std=400,
        monthly_expense_mean=1800,
        monthly_expense_std=300,
        months=6,
        n_sims=200,
        seed=7,
    )
    assert a["ending_balance"] == b["ending_balance"]
    assert a["p_ruin"] == b["p_ruin"]


def test_forecast_ruin_probability() -> None:
    """Start at $10, mean expense 1000, income 0 → always ruins."""
    result = run_cash_forecast(
        starting_balance=10,
        monthly_income_mean=0,
        monthly_expense_mean=1000,
        months=3,
        n_sims=100,
        seed=1,
    )
    assert result["p_ruin"] == 1.0
    assert result["ruin_count"] == 100


def test_forecast_p10_le_p50_le_p90() -> None:
    result = run_cash_forecast(
        starting_balance=2000,
        monthly_income_mean=3000,
        monthly_income_std=800,
        monthly_expense_mean=2800,
        monthly_expense_std=600,
        months=12,
        n_sims=500,
        seed=99,
    )
    eb = result["ending_balance"]
    assert eb["p10"] <= eb["p50"] <= eb["p90"]


# ── Scenarios ──────────────────────────────────────────────────────────────────


def test_scenario_delta_overlay() -> None:
    base = {"income": 50000, "annual_contribution": 5000, "disclaimer": "x"}
    out = what_if(base, delta={"annual_contribution": 1000}, label="boost")
    assert out["annual_contribution"] == 6000
    assert out["scenario"]["label"] == "boost"
    assert out["disclaimer"] == DISCLAIMER


def test_scenario_set_and_recompute() -> None:
    base = {"income": 40000, "annual_contribution": 2000}

    def recompute(inputs: dict) -> dict:
        return optimize_registered(
            income=float(inputs["income"]),
            age=25,
            first_time_buyer=False,
            horizon=1,
            annual_contribution=float(inputs["annual_contribution"]),
            tax_year=2026,
            growth_rate=0.0,
        )

    out = apply_overlay(
        base,
        {"set": {"annual_contribution": 7000}},
        recompute=recompute,
    )
    assert out["years"][0]["tfsa"] == 7000
    assert out["disclaimer"] == DISCLAIMER


# ── Router / tools smoke ───────────────────────────────────────────────────────


def test_planner_registered_endpoint(client) -> None:
    r = client.post(
        "/planner/registered",
        json={
            "income": 45000,
            "age": 22,
            "first_time_buyer": True,
            "horizon": 1,
            "annual_contribution": 8000,
            "tax_year": 2026,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["disclaimer"] == DISCLAIMER
    assert body["years"][0]["fhsa"] == 8000


def test_planner_osap_endpoint(client) -> None:
    r = client.post(
        "/planner/osap",
        json={"principal": 12000, "annual_rate": 0.0, "standard_years": 1.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["disclaimer"] == DISCLAIMER
    assert body["standard"]["monthly_payment"] == 1000.0


def test_planner_rules_endpoint(client) -> None:
    r = client.get("/planner/rules?year=2026")
    assert r.status_code == 200
    body = r.json()
    assert body["disclaimer"] == DISCLAIMER
    assert body["rules"]["tfsa_limit"] == 7000


def test_forecast_get_endpoint(client) -> None:
    r = client.get(
        "/forecast",
        params={
            "starting_balance": 1000,
            "monthly_income_mean": 500,
            "monthly_expense_mean": 300,
            "months": 12,
            "n_sims": 20,
            "seed": 1,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["disclaimer"] == DISCLAIMER
    assert body["ending_balance"]["p50"] == 3400.0


def test_agent_tools_registered() -> None:
    from agent.tools import TOOL_DEFINITIONS, execute_tool

    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert "run_registered_optimizer" in names
    assert "run_osap_plan" in names
    assert "run_cash_forecast" in names

    # execute_tool does not need db for planning tools
    class _Dummy:
        pass

    out = json.loads(
        execute_tool(
            "run_osap_plan",
            {"principal": 1000, "annual_rate": 0.0, "standard_years": 1},
            db=_Dummy(),  # type: ignore[arg-type]
        )
    )
    assert out["disclaimer"] == DISCLAIMER
    assert out["standard"]["monthly_payment"] == round(1000 / 12, 2)
