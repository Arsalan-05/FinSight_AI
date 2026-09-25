# ADR 0008: Monte Carlo forecasting

## Status

Accepted

## Context

Point forecasts hide ruin risk for students with irregular income.

## Decision

Bootstrap / fitted category distributions + scheduled items; 5,000 sims over 90–365 days; report P10/P50/P90 and P(balance < 0). Pure Python; LLM explains only.

## Consequences

- Backtest MAPE reported in docs
- Disclaimer: educational estimate, not advice
