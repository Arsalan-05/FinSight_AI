"""Canadian planning REST endpoints — registered accounts, OSAP, tax, forecast."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from planning import DISCLAIMER
from planning.forecast import run_cash_forecast
from planning.loader import available_years, load_rules
from planning.osap import plan_osap
from planning.registered import optimize_registered
from planning.scenarios import what_if
from planning.student_tax import estimate_tuition_credit

router = APIRouter(tags=["planner"])


def _with_disclaimer(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out["disclaimer"] = DISCLAIMER
    return out


# ── Request bodies ─────────────────────────────────────────────────────────────


class ExistingRoomIn(BaseModel):
    tfsa: float = 0.0
    rrsp: float = 0.0
    fhsa: float = 0.0
    fhsa_lifetime_contributed: float = 0.0


class RegisteredRequest(BaseModel):
    income: float = Field(..., ge=0)
    age: int = Field(..., ge=0, le=120)
    first_time_buyer: bool = False
    horizon: int = Field(5, ge=1, le=50)
    existing_room: Optional[ExistingRoomIn] = None
    annual_contribution: float = Field(0.0, ge=0)
    tax_year: int = 2026
    growth_rate: float = Field(0.05, ge=0, le=0.5)
    income_growth: float = Field(0.0, ge=-0.5, le=0.5)


class OsapRequest(BaseModel):
    principal: float = Field(..., ge=0)
    annual_rate: Optional[float] = Field(None, ge=0, le=1)
    standard_years: Optional[float] = Field(None, gt=0)
    accelerated_years: Optional[float] = Field(None, gt=0)
    extra_monthly: float = Field(0.0, ge=0)
    tax_year: int = 2026


class StudentTaxRequest(BaseModel):
    eligible_tuition: float = Field(..., ge=0)
    province: str = "ontario"
    tax_year: int = 2026
    carryforward_credits: float = Field(0.0, ge=0)


class ForecastRequest(BaseModel):
    starting_balance: float
    monthly_income_mean: float
    monthly_income_std: float = Field(0.0, ge=0)
    monthly_expense_mean: float
    monthly_expense_std: float = Field(0.0, ge=0)
    months: int = Field(12, ge=1, le=120)
    n_sims: int = Field(5000, ge=1, le=20000)
    seed: Optional[int] = None
    ruin_threshold: float = 0.0


class ScenarioRequest(BaseModel):
    base: dict[str, Any]
    set: Optional[dict[str, Any]] = None
    delta: Optional[dict[str, Any]] = None
    label: Optional[str] = None


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/planner/rules")
def get_planner_rules(
    year: int = Query(2026, description="Calendar year for CRA-style limits"),
) -> dict[str, Any]:
    """Return validated planning rules for a year."""
    try:
        rules = load_rules(year)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    data = rules.model_dump()
    return _with_disclaimer(
        {
            "rules": data,
            "available_years": available_years(),
        }
    )


@router.get("/planner/years")
def list_planner_years() -> dict[str, Any]:
    return _with_disclaimer({"available_years": available_years()})


@router.post("/planner/registered")
def post_registered_optimizer(body: RegisteredRequest) -> dict[str, Any]:
    """FHSA / TFSA / RRSP allocation optimizer with year-by-year projection."""
    try:
        result = optimize_registered(
            income=body.income,
            age=body.age,
            first_time_buyer=body.first_time_buyer,
            horizon=body.horizon,
            existing_room=(
                body.existing_room.model_dump() if body.existing_room else None
            ),
            annual_contribution=body.annual_contribution,
            tax_year=body.tax_year,
            growth_rate=body.growth_rate,
            income_growth=body.income_growth,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _with_disclaimer(result)


@router.post("/planner/osap")
def post_osap_plan(body: OsapRequest) -> dict[str, Any]:
    """OSAP repayment: standard vs accelerated vs extra payments."""
    try:
        result = plan_osap(
            principal=body.principal,
            annual_rate=body.annual_rate,
            standard_years=body.standard_years,
            accelerated_years=body.accelerated_years,
            extra_monthly=body.extra_monthly,
            tax_year=body.tax_year,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _with_disclaimer(result)


@router.post("/planner/student-tax")
def post_student_tax(body: StudentTaxRequest) -> dict[str, Any]:
    """Tuition credit estimate (clearly labeled as an estimate)."""
    try:
        result = estimate_tuition_credit(
            eligible_tuition=body.eligible_tuition,
            province=body.province,
            tax_year=body.tax_year,
            carryforward_credits=body.carryforward_credits,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _with_disclaimer(result)


@router.post("/planner/scenarios")
def post_scenario(body: ScenarioRequest) -> dict[str, Any]:
    """What-if overlay on a prior planner / forecast result."""
    result = what_if(
        body.base,
        set=body.set,
        delta=body.delta,
        label=body.label,
    )
    return _with_disclaimer(result)


@router.post("/forecast")
def post_forecast(body: ForecastRequest) -> dict[str, Any]:
    """Monte Carlo cash forecast with P10/P50/P90 and P(ruin)."""
    try:
        result = run_cash_forecast(
            starting_balance=body.starting_balance,
            monthly_income_mean=body.monthly_income_mean,
            monthly_income_std=body.monthly_income_std,
            monthly_expense_mean=body.monthly_expense_mean,
            monthly_expense_std=body.monthly_expense_std,
            months=body.months,
            n_sims=body.n_sims,
            seed=body.seed,
            ruin_threshold=body.ruin_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _with_disclaimer(result)


@router.get("/forecast")
def get_forecast(
    starting_balance: float = Query(...),
    monthly_income_mean: float = Query(...),
    monthly_expense_mean: float = Query(...),
    monthly_income_std: float = Query(0.0, ge=0),
    monthly_expense_std: float = Query(0.0, ge=0),
    months: int = Query(12, ge=1, le=120),
    n_sims: int = Query(5000, ge=1, le=20000),
    seed: Optional[int] = Query(None),
    ruin_threshold: float = Query(0.0),
) -> dict[str, Any]:
    """GET variant of Monte Carlo forecast (query params)."""
    try:
        result = run_cash_forecast(
            starting_balance=starting_balance,
            monthly_income_mean=monthly_income_mean,
            monthly_income_std=monthly_income_std,
            monthly_expense_mean=monthly_expense_mean,
            monthly_expense_std=monthly_expense_std,
            months=months,
            n_sims=n_sims,
            seed=seed,
            ruin_threshold=ruin_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _with_disclaimer(result)
