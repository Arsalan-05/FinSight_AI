"""Canadian student demo transactions (Jan–Mar 2026) — RBC + Simplii."""

from __future__ import annotations

from datetime import date

from db.models import Transaction

_JANUARY = [
    (1, "checking", "OSAP Disbursement", 3200.00, "Income", "OSAP"),
    (2, "credit", "Loblaws Groceries", -86.44, "Groceries", "Loblaws"),
    (3, "credit", "INTERAC E-TRANSFER SENT - RENT JAN", -950.00, "Housing", "Landlord"),
    (5, "credit", "Tim Hortons", -6.85, "Dining", "Tim Hortons"),
    (6, "checking", "Co-op Paycheque", 2800.00, "Income", "Employer"),
    (8, "credit", "TTC Presto Load", -156.00, "Transport", "TTC"),
    (10, "credit", "Amazon.ca", -54.99, "Shopping", "Amazon"),
    (12, "credit", "Spotify Premium", -11.99, "Subscriptions", "Spotify"),
    (14, "credit", "INTERAC E-TRANSFER SENT - AHMED", -120.00, "Transfers", "Ahmed"),
    (15, "checking", "Rogers Internet", -74.99, "Utilities", "Rogers"),
    (17, "credit", "Petro-Canada Gas", -62.30, "Transport", "Petro-Canada"),
    (19, "credit", "Metro Groceries", -48.20, "Groceries", "Metro"),
    (21, "checking", "York U Gym", -35.00, "Health", "York University"),
    (23, "credit", "Uber Eats", -32.50, "Dining", "Uber Eats"),
    (25, "credit", "Canadian Tire", -38.99, "Shopping", "Canadian Tire"),
    (27, "credit", "Cineplex Movies", -28.00, "Entertainment", "Cineplex"),
    (28, "checking", "Hydro One", -94.20, "Utilities", "Hydro One"),
]

_FEBRUARY = [
    (1, "checking", "Co-op Paycheque", 2800.00, "Income", "Employer"),
    (2, "credit", "Costco Wholesale", -128.60, "Groceries", "Costco"),
    (3, "credit", "INTERAC E-TRANSFER SENT - RENT FEB", -950.00, "Housing", "Landlord"),
    (6, "credit", "Popeyes Louisiana Kitchen", -15.40, "Dining", "Popeyes"),
    (8, "credit", "TTC Presto Load", -156.00, "Transport", "TTC"),
    (10, "credit", "Apple Store", -149.00, "Shopping", "Apple"),
    (12, "credit", "Netflix", -18.99, "Subscriptions", "Netflix"),
    (14, "credit", "Shoppers Drug Mart", -24.45, "Health", "Shoppers"),
    (15, "checking", "Rogers Internet", -74.99, "Utilities", "Rogers"),
    (17, "credit", "Swiss Chalet", -42.90, "Dining", "Swiss Chalet"),
    (19, "credit", "Petro-Canada Gas", -58.10, "Transport", "Petro-Canada"),
    (20, "checking", "TFSA Transfer", -500.00, "Savings", "RBC TFSA"),
    (22, "credit", "Loblaws Groceries", -91.33, "Groceries", "Loblaws"),
    (24, "credit", "Best Buy", -199.99, "Shopping", "Best Buy"),
    (26, "credit", "INTERAC E-TRANSFER RECEIVED - MOM", 200.00, "Income", "Family"),
    (28, "checking", "Hydro One", -88.15, "Utilities", "Hydro One"),
]

_MARCH = [
    (1, "checking", "Co-op Paycheque", 2800.00, "Income", "Employer"),
    (2, "credit", "No Frills Groceries", -71.80, "Groceries", "No Frills"),
    (3, "credit", "INTERAC E-TRANSFER SENT - RENT MAR", -950.00, "Housing", "Landlord"),
    (5, "credit", "Freshii", -16.50, "Dining", "Freshii"),
    (8, "credit", "TTC Presto Load", -156.00, "Transport", "TTC"),
    (10, "credit", "Sport Chek", -89.00, "Shopping", "Sport Chek"),
    (12, "credit", "Spotify Premium", -11.99, "Subscriptions", "Spotify"),
    (13, "credit", "Starbucks", -7.75, "Dining", "Starbucks"),
    (15, "checking", "Rogers Internet", -74.99, "Utilities", "Rogers"),
    (17, "credit", "Petro-Canada Gas", -55.90, "Transport", "Petro-Canada"),
    (19, "credit", "Walmart Groceries", -62.05, "Groceries", "Walmart"),
    (20, "checking", "York U Gym", -35.00, "Health", "York University"),
    (22, "credit", "Chipotle", -17.25, "Dining", "Chipotle"),
    (24, "credit", "Amazon.ca", -63.40, "Shopping", "Amazon"),
    (26, "credit", "Bowling", -38.00, "Entertainment", "Bowlero"),
    (28, "checking", "Hydro One", -82.60, "Utilities", "Hydro One"),
    (30, "credit", "Pharmacy", -18.50, "Health", "Shoppers"),
]

_MONTHS = [(1, _JANUARY), (2, _FEBRUARY), (3, _MARCH)]


def prior_month_transactions(checking_id: str, credit_id: str) -> list[Transaction]:
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
