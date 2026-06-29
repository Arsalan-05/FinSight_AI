"""Proactive financial insights engine."""

from insights.anomalies import detect_anomalies
from insights.credit_optimizer import credit_card_tips
from insights.reconciliation import reconcile_accounts
from insights.recurring import detect_recurring_charges
from insights.runway import analyze_cash_runway
from insights.tfsa import tfsa_contribution_status

__all__ = [
    "detect_anomalies",
    "credit_card_tips",
    "detect_recurring_charges",
    "reconcile_accounts",
    "analyze_cash_runway",
    "tfsa_contribution_status",
    "build_all_insights",
]

from insights.service import build_all_insights  # noqa: E402
