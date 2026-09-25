"""Load and validate year-specific Canadian planning rules from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

RULES_DIR = Path(__file__).resolve().parent / "rules"


class TaxBracket(BaseModel):
    """Simplified tax bracket: rate applies up to ``up_to`` (None = unlimited)."""

    up_to: Optional[float] = None
    rate: float

    @field_validator("rate")
    @classmethod
    def rate_in_unit_interval(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("rate must be between 0 and 1")
        return v

    @field_validator("up_to")
    @classmethod
    def up_to_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("up_to must be positive when set")
        return v


class OsapRules(BaseModel):
    interest_rate: float = Field(..., ge=0.0, le=1.0)
    standard_amortization_years: float = Field(..., gt=0.0)


class PlanningRules(BaseModel):
    year: int
    tfsa_limit: float = Field(..., gt=0)
    rrsp_limit: float = Field(..., gt=0)
    fhsa_limit: float = Field(..., gt=0)
    fhsa_lifetime_cap: float = Field(..., gt=0)
    federal_tax_brackets: list[TaxBracket]
    ontario_brackets: list[TaxBracket]
    osap: OsapRules
    sources: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def brackets_ordered(self) -> PlanningRules:
        for name, brackets in (
            ("federal_tax_brackets", self.federal_tax_brackets),
            ("ontario_brackets", self.ontario_brackets),
        ):
            if not brackets:
                raise ValueError(f"{name} must be non-empty")
            prev: Optional[float] = 0.0
            for i, b in enumerate(brackets):
                if b.up_to is None:
                    if i != len(brackets) - 1:
                        raise ValueError(f"{name}: null up_to only allowed on last bracket")
                else:
                    if prev is not None and b.up_to <= prev:
                        raise ValueError(f"{name}: up_to values must be strictly increasing")
                    prev = b.up_to
            if brackets[-1].up_to is not None:
                raise ValueError(f"{name}: last bracket must have up_to: null")
        if self.fhsa_lifetime_cap < self.fhsa_limit:
            raise ValueError("fhsa_lifetime_cap must be >= fhsa_limit")
        return self


def _rules_path(year: int) -> Path:
    return RULES_DIR / f"{year}.yaml"


def available_years() -> list[int]:
    """Return years that have a rules YAML file."""
    years: list[int] = []
    if not RULES_DIR.is_dir():
        return years
    for path in sorted(RULES_DIR.glob("*.yaml")):
        try:
            years.append(int(path.stem))
        except ValueError:
            continue
    return years


def load_rules(year: int) -> PlanningRules:
    """Load and validate planning rules for ``year``.

    Raises:
        FileNotFoundError: if no YAML exists for the year.
        ValueError / pydantic.ValidationError: if schema is invalid.
    """
    path = _rules_path(year)
    if not path.is_file():
        available = ", ".join(str(y) for y in available_years()) or "(none)"
        raise FileNotFoundError(
            f"No planning rules for year {year}. Available: {available}"
        )
    with path.open(encoding="utf-8") as fh:
        raw: Any = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"Rules file {path.name} must be a YAML mapping")
    return PlanningRules.model_validate(raw)


def marginal_rate(
    taxable_income: float,
    brackets: list[TaxBracket],
) -> float:
    """Return the marginal rate for ``taxable_income`` given ordered brackets."""
    if taxable_income < 0:
        taxable_income = 0.0
    for bracket in brackets:
        if bracket.up_to is None or taxable_income <= bracket.up_to:
            return bracket.rate
    return brackets[-1].rate


def combined_marginal_rate(rules: PlanningRules, taxable_income: float) -> float:
    """Federal + Ontario marginal rate (simplified; ignores surtax)."""
    fed = marginal_rate(taxable_income, rules.federal_tax_brackets)
    ont = marginal_rate(taxable_income, rules.ontario_brackets)
    return round(fed + ont, 6)


def tax_on_income(taxable_income: float, brackets: list[TaxBracket]) -> float:
    """Compute progressive tax for ``taxable_income`` under ``brackets``."""
    if taxable_income <= 0:
        return 0.0
    tax = 0.0
    lower = 0.0
    for bracket in brackets:
        upper = bracket.up_to if bracket.up_to is not None else taxable_income
        slice_top = min(taxable_income, upper)
        if slice_top > lower:
            tax += (slice_top - lower) * bracket.rate
        if bracket.up_to is None or taxable_income <= bracket.up_to:
            break
        lower = bracket.up_to
    return round(tax, 2)
