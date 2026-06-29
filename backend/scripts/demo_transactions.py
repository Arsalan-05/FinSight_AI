"""Synthetic transaction templates for demo seed data (Jan–Mar 2026)."""

from __future__ import annotations

from datetime import date

from db.models import Transaction

# (day, account: checking|credit, description, amount, category, merchant)
_JANUARY = [
    (1, "checking", "Salary Deposit", 4500.00, "Income", "Acme Corp"),
    (2, "credit", "Whole Foods Market", -118.22, "Groceries", "Whole Foods"),
    (3, "credit", "Netflix Subscription", -15.99, "Subscriptions", "Netflix"),
    (5, "credit", "Chipotle Mexican Grill", -13.40, "Dining", "Chipotle"),
    (6, "checking", "Rent Payment", -1800.00, "Housing", "Landlord LLC"),
    (8, "credit", "Uber Ride", -11.80, "Transport", "Uber"),
    (10, "credit", "Amazon Purchase", -67.50, "Shopping", "Amazon"),
    (12, "credit", "Spotify Premium", -9.99, "Subscriptions", "Spotify"),
    (14, "credit", "Starbucks Coffee", -7.25, "Dining", "Starbucks"),
    (15, "checking", "Internet Bill", -59.99, "Utilities", "Verizon"),
    (17, "credit", "Shell Gas Station", -48.30, "Transport", "Shell"),
    (19, "credit", "Trader Joe's", -54.10, "Groceries", "Trader Joe's"),
    (21, "checking", "Gym Membership", -49.00, "Health", "Equinox"),
    (23, "credit", "DoorDash Delivery", -28.75, "Dining", "DoorDash"),
    (25, "credit", "Target", -42.18, "Shopping", "Target"),
    (27, "credit", "Movie Tickets", -32.00, "Entertainment", "AMC"),
    (28, "checking", "Electric Bill", -87.40, "Utilities", "Con Edison"),
]

_FEBRUARY = [
    (1, "checking", "Salary Deposit", 4500.00, "Income", "Acme Corp"),
    (2, "credit", "Costco Wholesale", -142.60, "Groceries", "Costco"),
    (3, "credit", "Netflix Subscription", -15.99, "Subscriptions", "Netflix"),
    (6, "checking", "Rent Payment", -1800.00, "Housing", "Landlord LLC"),
    (7, "credit", "Panera Bread", -16.20, "Dining", "Panera"),
    (9, "credit", "Lyft Ride", -14.10, "Transport", "Lyft"),
    (11, "credit", "Apple Store", -129.00, "Shopping", "Apple"),
    (12, "credit", "Spotify Premium", -9.99, "Subscriptions", "Spotify"),
    (14, "credit", "CVS Pharmacy", -22.45, "Health", "CVS"),
    (15, "checking", "Internet Bill", -59.99, "Utilities", "Verizon"),
    (17, "credit", "Cheesecake Factory", -58.90, "Dining", "Cheesecake Factory"),
    (19, "credit", "Shell Gas Station", -51.20, "Transport", "Shell"),
    (20, "checking", "Gym Membership", -49.00, "Health", "Equinox"),
    (22, "credit", "Whole Foods Market", -96.33, "Groceries", "Whole Foods"),
    (24, "credit", "Best Buy", -189.99, "Shopping", "Best Buy"),
    (26, "credit", "Concert Tickets", -95.00, "Entertainment", "Ticketmaster"),
    (28, "checking", "Electric Bill", -92.15, "Utilities", "Con Edison"),
]

_MARCH = [
    (1, "checking", "Salary Deposit", 4500.00, "Income", "Acme Corp"),
    (2, "credit", "Trader Joe's", -61.80, "Groceries", "Trader Joe's"),
    (3, "credit", "Netflix Subscription", -15.99, "Subscriptions", "Netflix"),
    (5, "credit", "Sweetgreen", -18.50, "Dining", "Sweetgreen"),
    (6, "checking", "Rent Payment", -1800.00, "Housing", "Landlord LLC"),
    (8, "credit", "Uber Ride", -13.60, "Transport", "Uber"),
    (10, "credit", "Nike Store", -98.00, "Shopping", "Nike"),
    (12, "credit", "Spotify Premium", -9.99, "Subscriptions", "Spotify"),
    (13, "credit", "Starbucks Coffee", -8.75, "Dining", "Starbucks"),
    (15, "checking", "Internet Bill", -59.99, "Utilities", "Verizon"),
    (17, "credit", "Shell Gas Station", -49.90, "Transport", "Shell"),
    (19, "credit", "Whole Foods Market", -112.05, "Groceries", "Whole Foods"),
    (20, "checking", "Gym Membership", -49.00, "Health", "Equinox"),
    (22, "credit", "Chipotle Mexican Grill", -14.25, "Dining", "Chipotle"),
    (24, "credit", "Amazon Purchase", -73.40, "Shopping", "Amazon"),
    (26, "credit", "Bowling Night", -45.00, "Entertainment", "Bowlero"),
    (28, "checking", "Electric Bill", -78.60, "Utilities", "Con Edison"),
    (30, "credit", "Pharmacy Prescription", -16.50, "Health", "Walgreens"),
]

_MONTHS: list[tuple[int, list]] = [
    (1, _JANUARY),
    (2, _FEBRUARY),
    (3, _MARCH),
]


def prior_month_transactions(checking_id: str, credit_id: str) -> list[Transaction]:
    """Build Jan–Mar 2026 transactions for demo accounts."""
    txs: list[Transaction] = []
    for month, rows in _MONTHS:
        for day, account, description, amount, category, merchant in rows:
            account_id = checking_id if account == "checking" else credit_id
            txs.append(
                Transaction(
                    account_id=account_id,
                    transaction_date=date(2026, month, day),
                    description=description,
                    amount=amount,
                    category=category,
                    merchant=merchant,
                )
            )
    return txs
