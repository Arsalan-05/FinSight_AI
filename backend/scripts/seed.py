"""Seed the database with a realistic 3-month transaction history.

Run with:
    uv run python scripts/seed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# allow importing from backend root
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date

from db.base import Base, SessionLocal, engine
from db.models import Account, Transaction, User


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Idempotent: skip if already seeded
    if db.query(User).filter(User.email == "demo@finsight.ai").first():
        print("Already seeded — skipping.")
        db.close()
        return

    user = User(email="demo@finsight.ai", name="Demo User")
    db.add(user)
    db.flush()

    checking = Account(
        user_id=user.id,
        name="Primary Checking",
        institution="Chase",
        account_type="checking",
    )
    credit = Account(
        user_id=user.id,
        name="Sapphire Reserve",
        institution="Chase",
        account_type="credit",
    )
    db.add_all([checking, credit])
    db.flush()

    transactions = [
        # ── April ─────────────────────────────────────────────────────────────
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 4, 1),
            description="Salary Deposit",
            amount=4500.00,
            category="Income",
            merchant="Acme Corp",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 2),
            description="Whole Foods Market",
            amount=-127.43,
            category="Groceries",
            merchant="Whole Foods",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 3),
            description="Netflix Subscription",
            amount=-15.99,
            category="Subscriptions",
            merchant="Netflix",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 5),
            description="Chipotle Mexican Grill",
            amount=-14.75,
            category="Dining",
            merchant="Chipotle",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 4, 6),
            description="Rent Payment",
            amount=-1800.00,
            category="Housing",
            merchant="Landlord LLC",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 8),
            description="Uber Ride",
            amount=-12.50,
            category="Transport",
            merchant="Uber",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 10),
            description="Amazon Prime",
            amount=-139.00,
            category="Subscriptions",
            merchant="Amazon",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 11),
            description="Starbucks Coffee",
            amount=-6.75,
            category="Dining",
            merchant="Starbucks",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 14),
            description="Spotify Premium",
            amount=-9.99,
            category="Subscriptions",
            merchant="Spotify",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 15),
            description="Trader Joe's",
            amount=-89.20,
            category="Groceries",
            merchant="Trader Joe's",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 17),
            description="AMC Theaters",
            amount=-32.00,
            category="Entertainment",
            merchant="AMC",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 19),
            description="Shell Gas Station",
            amount=-55.40,
            category="Transport",
            merchant="Shell",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 4, 20),
            description="Gym Membership",
            amount=-49.00,
            category="Health",
            merchant="Equinox",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 22),
            description="Sweetgreen Salad",
            amount=-18.50,
            category="Dining",
            merchant="Sweetgreen",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 25),
            description="CVS Pharmacy",
            amount=-23.15,
            category="Health",
            merchant="CVS",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 27),
            description="The Cheesecake Factory",
            amount=-74.90,
            category="Dining",
            merchant="The Cheesecake Factory",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 4, 29),
            description="Target",
            amount=-112.33,
            category="Shopping",
            merchant="Target",
        ),
        # ── May ───────────────────────────────────────────────────────────────
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 5, 1),
            description="Salary Deposit",
            amount=4500.00,
            category="Income",
            merchant="Acme Corp",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 2),
            description="Whole Foods Market",
            amount=-143.60,
            category="Groceries",
            merchant="Whole Foods",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 3),
            description="Netflix Subscription",
            amount=-15.99,
            category="Subscriptions",
            merchant="Netflix",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 5, 6),
            description="Rent Payment",
            amount=-1800.00,
            category="Housing",
            merchant="Landlord LLC",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 7),
            description="Shake Shack",
            amount=-22.10,
            category="Dining",
            merchant="Shake Shack",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 9),
            description="Apple One Subscription",
            amount=-19.95,
            category="Subscriptions",
            merchant="Apple",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 11),
            description="Lyft Ride",
            amount=-9.75,
            category="Transport",
            merchant="Lyft",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 13),
            description="Trader Joe's",
            amount=-95.80,
            category="Groceries",
            merchant="Trader Joe's",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 15),
            description="Spotify Premium",
            amount=-9.99,
            category="Subscriptions",
            merchant="Spotify",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 16),
            description="Nike Store",
            amount=-189.00,
            category="Shopping",
            merchant="Nike",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 5, 18),
            description="Electric Bill",
            amount=-87.50,
            category="Utilities",
            merchant="ConEd",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 20),
            description="Starbucks Coffee",
            amount=-7.25,
            category="Dining",
            merchant="Starbucks",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 22),
            description="BookDepository",
            amount=-34.99,
            category="Education",
            merchant="BookDepository",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 24),
            description="Shell Gas Station",
            amount=-60.10,
            category="Transport",
            merchant="Shell",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 5, 25),
            description="Gym Membership",
            amount=-49.00,
            category="Health",
            merchant="Equinox",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 27),
            description="Sushi Restaurant",
            amount=-65.40,
            category="Dining",
            merchant="Nobu",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 5, 29),
            description="Amazon Purchase",
            amount=-47.99,
            category="Shopping",
            merchant="Amazon",
        ),
        # ── June ──────────────────────────────────────────────────────────────
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 6, 1),
            description="Salary Deposit",
            amount=4500.00,
            category="Income",
            merchant="Acme Corp",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 2),
            description="Whole Foods Market",
            amount=-118.75,
            category="Groceries",
            merchant="Whole Foods",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 3),
            description="Netflix Subscription",
            amount=-15.99,
            category="Subscriptions",
            merchant="Netflix",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 6, 6),
            description="Rent Payment",
            amount=-1800.00,
            category="Housing",
            merchant="Landlord LLC",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 8),
            description="Uber Eats",
            amount=-38.50,
            category="Dining",
            merchant="Uber Eats",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 10),
            description="Trader Joe's",
            amount=-102.40,
            category="Groceries",
            merchant="Trader Joe's",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 12),
            description="Spotify Premium",
            amount=-9.99,
            category="Subscriptions",
            merchant="Spotify",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 14),
            description="H&M Online",
            amount=-76.00,
            category="Shopping",
            merchant="H&M",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 6, 15),
            description="Internet Bill",
            amount=-59.99,
            category="Utilities",
            merchant="Verizon",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 17),
            description="Chipotle Mexican Grill",
            amount=-13.95,
            category="Dining",
            merchant="Chipotle",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 19),
            description="Shell Gas Station",
            amount=-52.80,
            category="Transport",
            merchant="Shell",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 6, 20),
            description="Gym Membership",
            amount=-49.00,
            category="Health",
            merchant="Equinox",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 22),
            description="Starbucks Coffee",
            amount=-8.10,
            category="Dining",
            merchant="Starbucks",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 24),
            description="Concert Tickets",
            amount=-120.00,
            category="Entertainment",
            merchant="Ticketmaster",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 26),
            description="Pharmacy Prescription",
            amount=-18.00,
            category="Health",
            merchant="Walgreens",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 27),
            description="Best Buy",
            amount=-249.99,
            category="Shopping",
            merchant="Best Buy",
        ),
    ]

    db.add_all(transactions)
    db.commit()
    db.close()
    print(f"Seeded 1 user, 2 accounts, {len(transactions)} transactions.")


if __name__ == "__main__":
    seed()
