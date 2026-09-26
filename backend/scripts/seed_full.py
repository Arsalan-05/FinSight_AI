"""Fill one user's account with 13 months of realistic Canadian student data.

Wipes the user's financial data (accounts, transactions, embeddings, leak findings,
budgets, notifications) and rebuilds it so every feature has something to show:
Overview, analytics, subscriptions, money leaks, TFSA, runway, budgets and alerts,
goals, weekly brief, anomalies and semantic search. Chat history is left alone.

Dates are relative to today, so "last month" always has data.

Run:
    uv run python scripts/seed_full.py --email you@example.com
    uv run python scripts/seed_full.py --email you@example.com --dry-run   # validate only
    uv run python scripts/seed_full.py --email you@example.com --no-embed  # skip Voyage
"""

from __future__ import annotations

import argparse
import calendar
import json
import random
import sys
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@dataclass
class SeedTx:
    transaction_date: date
    account: str
    description: str
    amount: float
    category: str
    merchant: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


# Everyday merchants. Amounts alternate between a low and a high band so no merchant
# looks like a fixed-price subscription (the leak detectors flag similar amounts).
# Frequent merchants: visit gap stays under 20 days. Rare merchants: at least 50 days
# apart. Gaps of 20-45 days would read as "monthly" and trigger false price-creep leaks.
_FREQUENT = [
    # merchant, account, category, description, low band, high band, gap days
    ("No Frills", "chq", "Groceries", "NO FRILLS #3412 TORONTO ON", (18, 38), (62, 98), (5, 9)),
    ("Loblaws", "visa", "Groceries", "LOBLAWS #1088 TORONTO ON", (12, 28), (48, 78), (9, 15)),
    ("Tim Hortons", "chq", "Dining", "TIM HORTONS #2217 NORTH YORK", (3.2, 5.8), (9.5, 15.9), (2, 6)),
    ("Starbucks", "visa", "Dining", "STARBUCKS #4471 YORK UNIVERSITY", (4.9, 7.2), (11.5, 18.4), (8, 15)),
    ("Uber Eats", "visa", "Dining", "UBER* EATS TORONTO ON", (17, 25), (38, 58), (8, 14)),
    ("McDonald's", "chq", "Dining", "MCDONALD'S #40512 NORTH YORK", (6, 9.5), (15, 22), (9, 16)),
    ("Uber", "visa", "Transport", "UBER* TRIP TORONTO ON", (9, 14), (24, 39), (10, 17)),
    ("Amazon.ca", "visa", "Shopping", "AMAZON.CA*MK2J81 AMAZON.CA", (12, 28), (55, 120), (9, 15)),
    ("Shoppers Drug Mart", "chq", "Healthcare", "SHOPPERS DRUG MART #1297", (6, 15), (32, 58), (10, 17)),
    ("Dollarama", "chq", "Shopping", "DOLLARAMA #845 TORONTO ON", (4.5, 8), (16, 28), (12, 18)),
]

_RARE = [
    ("Osmow's", "chq", "Dining", "OSMOW'S SHAWARMA KEELE ST", (14, 19), (36, 48)),
    ("Pizza Pizza", "chq", "Dining", "PIZZA PIZZA #512 TORONTO", (12, 17), (31, 45)),
    ("Pai Northern Thai", "visa", "Dining", "PAI NORTHERN THAI KITCHEN", (24, 32), (58, 76)),
    ("Burrito Boyz", "chq", "Dining", "BURRITO BOYZ QUEEN ST W", (13, 16), (28, 36)),
    ("FreshCo", "chq", "Groceries", "FRESHCO #9921 TORONTO ON", (15, 30), (55, 90)),
    ("Costco Wholesale", "visa", "Groceries", "COSTCO WHOLESALE #535", (45, 80), (160, 260)),
    ("Winners", "visa", "Shopping", "WINNERS #288 YORKDALE", (15, 30), (60, 110)),
    ("Uniqlo", "visa", "Shopping", "UNIQLO EATON CENTRE", (19.9, 34.9), (79.9, 129.9)),
    ("Best Buy", "visa", "Shopping", "BEST BUY #936 TORONTO", (19.99, 39.99), (119.99, 249.99)),
    ("IKEA", "visa", "Shopping", "IKEA NORTH YORK ON", (12, 29), (89, 179)),
    ("Indigo Eaton Centre", "visa", "Shopping", "INDIGO EATON CENTRE", (11, 24), (45, 78)),
    ("H&M", "visa", "Shopping", "H&M YORKDALE MALL", (14.99, 29.99), (69.99, 119.99)),
    ("Cineplex", "visa", "Entertainment", "CINEPLEX SCOTIABANK TORONTO", (13.99, 19.99), (38, 54)),
    ("GO Transit", "chq", "Transport", "GO TRANSIT PRESTO FARE", (9.5, 14), (24, 32)),
]

_RARE_MIN_GAP = 50


def _last_day(d: date) -> int:
    return calendar.monthrange(d.year, d.month)[1]


def _on(month_start: date, day: int) -> date:
    return month_start.replace(day=min(day, _last_day(month_start)))


def _month_starts(start: date, today: date) -> list[date]:
    out = []
    d = start
    while d <= today:
        out.append(d)
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


class Builder:
    def __init__(self, today: date, seed: int = 20260926) -> None:
        self.today = today
        self.rng = random.Random(seed)
        self.txs: list[SeedTx] = []
        self.year_start = date(today.year, 1, 2)

    def add(
        self,
        d: date,
        account: str,
        description: str,
        amount: float,
        category: str,
        merchant: Optional[str] = None,
    ) -> Optional[SeedTx]:
        if d > self.today:
            return None
        tx = SeedTx(d, account, description, round(amount, 2), category, merchant)
        self.txs.append(tx)
        return tx

    def ago(self, days: int) -> date:
        """A date `days` before today, kept inside the current calendar year."""
        return max(self.today - timedelta(days=days), self.year_start)

    def band(self, band: tuple[float, float]) -> float:
        return round(self.rng.uniform(*band), 2)


def build_transactions(today: date, fx_rates: dict) -> list[SeedTx]:
    from leaks.boc import nearest_rate

    b = Builder(today)
    rng = b.rng
    start = date(today.year - 1, today.month, 1)
    months = _month_starts(start, today)

    # ── Fixed monthly bills and subscriptions ───────────────────────────────────
    spotify_raise = months[-7]
    rogers_raise = months[-4]
    for i, ms in enumerate(months):
        b.add(ms, "chq", "INTERAC E-TRANSFER - RENT TO K. PATEL (LANDLORD)", -1150.00,
              "Housing", "Landlord Rent (e-Transfer)")
        b.add(ms, "chq", "PRESTO MONTHLY PASS - TTC POST-SECONDARY", -128.15,
              "Transport", "PRESTO Monthly Pass")
        b.add(_on(ms, 7), "visa", "SPOTIFY P3F9A2 STOCKHOLM",
              -12.99 if ms >= spotify_raise else -11.99, "Subscriptions", "Spotify")
        b.add(_on(ms, 12), "visa", "APPLE.COM/BILL ICLOUD+ 50GB", -3.99,
              "Subscriptions", "Apple iCloud+")
        b.add(_on(ms, 18), "visa", "ROGERS WIRELESS PAD",
              -71.19 if ms >= rogers_raise else -65.54, "Utilities", "Rogers Wireless")
        # Planted leak: gym membership with no other gym activity.
        if i >= 2:
            b.add(_on(ms, 15), "chq", "GOODLIFE FITNESS CLUBS MEMBERSHIP", -54.99,
                  "Subscriptions", "GoodLife Fitness")
        # Planted leak: streaming service signed up for and forgotten.
        if i >= len(months) - 8:
            b.add(_on(ms, 22), "visa", "CRAVE BELL MEDIA", -22.59, "Subscriptions", "Crave")
        # Monthly savings sweep into the high-interest account.
        label = ms.strftime("%b %Y")
        b.add(_on(ms, 16), "chq", "TRANSFER TO RBC HIGH INTEREST ESAVINGS", -200.00,
              "Transfers", f"RBC HISA Transfer ({label})")
        b.add(_on(ms, 16), "hisa", "TRANSFER FROM RBC CHEQUING", 200.00, "Transfers")

    # HISA interest (3.5%/yr on a growing balance)
    balance = 1800.0
    for ms in months:
        balance += 200
        end = _on(ms, 31)
        if end < today:
            interest = round(balance * 0.035 / 12, 2)
            balance += interest
            b.add(end, "hisa", "INTEREST PAID", interest, "Income")

    # ── Income ──────────────────────────────────────────────────────────────────
    payday = start + timedelta(days=(4 - start.weekday()) % 7)  # first Friday
    while payday <= today:
        if 5 <= payday.month <= 8:
            b.add(payday, "chq", "PAYROLL DEPOSIT SHOPIFY INC", 2236.54, "Income")
        else:
            hours_pay = rng.uniform(820, 960) if payday.month == 12 else rng.uniform(540, 790)
            b.add(payday, "chq", "PAYROLL DEPOSIT INDIGO BOOKS & MUSIC", hours_pay, "Income")
        payday += timedelta(days=14)

    tuition = 3510.75
    textbooks = [186.40, 142.15, 97.60, 84.30]
    term = 0
    for ms in months:
        if ms.month in (9, 1):
            b.add(_on(ms, 3), "chq", "OSAP DISBURSEMENT - NSLSC", rng.uniform(3900, 4300), "Income")
            b.add(_on(ms, 8), "chq", "YORK UNIVERSITY TUITION PAYMENT", -tuition,
                  "Education", "York University")
            tuition -= rng.uniform(15, 330)  # never higher than last term
            b.add(_on(ms, 10), "chq", "YORK U BOOKSTORE", -textbooks[min(term, 3)],
                  "Education", "York U Bookstore")
            term += 1
    for ms in months[1::2]:
        b.add(_on(ms, 20), "chq", "INTERAC E-TRANSFER FROM AMIR ALI", 300.00, "Transfers")

    # ── TFSA: contributions land as credits in the TFSA account ─────────────────
    tfsa_dates = [(date(today.year - 1, 10, 15), 1500.00)]
    tfsa_dates += [(date(today.year, 1, 15), 1000.00), (date(today.year, 4, 20), 2500.00),
                   (date(today.year, 8, 5), 2000.00)]
    for d, amt in tfsa_dates:
        if start <= d <= today:
            b.add(d, "chq", "TRANSFER TO WEALTHSIMPLE TFSA", -amt, "Savings",
                  f"Wealthsimple TFSA Contribution ({d:%b %Y})")
            b.add(d, "tfsa", "TFSA CONTRIBUTION FROM RBC CHEQUING", amt, "Savings")
    for ms in months:
        if ms.month in (3, 6, 9, 12):
            b.add(_on(ms, 28), "tfsa", "DIVIDEND XEQT ISHARES CORE EQUITY", rng.uniform(8, 25), "Income")

    # ── Everyday spending ───────────────────────────────────────────────────────
    next_visit = {m[0]: start + timedelta(days=rng.randint(0, m[6][1])) for m in _FREQUENT}
    band_toggle = {m[0]: rng.random() < 0.5 for m in _FREQUENT + _RARE}
    last_rare: dict[str, date] = {}

    def spend(name: str, low: tuple, high: tuple) -> float:
        band_toggle[name] = not band_toggle[name]
        return b.band(high if band_toggle[name] else low)

    d = start
    while d <= today:
        for name, acct, cat, desc, low, high, (gmin, gmax) in _FREQUENT:
            if d >= next_visit[name]:
                b.add(d, acct, desc, -spend(name, low, high), cat, name)
                next_visit[name] = d + timedelta(days=rng.randint(gmin, gmax))
        for name, acct, cat, desc, low, high in _RARE:
            prev = last_rare.get(name)
            if (prev is None or (d - prev).days >= _RARE_MIN_GAP) and rng.random() < 1 / 40:
                b.add(d, acct, desc, -spend(name, low, high), cat, name)
                last_rare[name] = d
        d += timedelta(days=1)

    # ── Related activity so real subscriptions aren't flagged as forgotten ──────
    b.add(today - timedelta(days=40), "chq", "PRESTO FARE UP EXPRESS PEARSON", -12.35,
          "Transport", "UP Express")
    b.add(today - timedelta(days=35), "visa", "APPLE STORE EATON CENTRE", -35.03,
          "Shopping", "Apple Store Eaton Centre")
    b.add(today - timedelta(days=37), "visa", "TICKETMASTER *SPOTIFY FAN PRESALE", -148.40,
          "Entertainment", "Ticketmaster")

    # ── NYC trip (FX charges on the Visa, roaming, foreign ATM) ────────────────
    trip = today - timedelta(days=78)
    b.add(trip, "visa", "ROGERS ROAMING PASS - USA", -14.69, "Utilities", "Rogers Roaming")

    # ── Planted money leaks (current calendar year) ─────────────────────────────
    def fx_charge(days_ago: int, desc: str, code: str, foreign: float, cat: str, merchant: str) -> None:
        when = b.ago(days_ago)
        rate = nearest_rate(fx_rates, when, f"{code}CAD") or 1.37
        cad = round(foreign * rate * 1.025, 2)  # 2.5% card FX markup
        b.add(when, "visa", f"{desc} {code} {foreign:.2f}", -cad, cat, merchant)

    fx_charge(250, "AMAZON.COM*US", "USD", 42.99, "Shopping", "Amazon.com US")
    fx_charge(229, "STEAMGAMES.COM", "USD", 29.99, "Entertainment", "Steam")
    fx_charge(196, "ETSY.COM", "USD", 18.50, "Shopping", "Etsy")
    fx_charge(147, "NIKE.COM", "USD", 110.00, "Shopping", "Nike US")
    fx_charge(115, "BOOKING.COM", "EUR", 85.00, "Travel", "Booking.com")
    fx_charge(78, "AIRBNB * HMXQ4T", "USD", 312.00, "Travel", "Airbnb")
    fx_charge(77, "JOES PIZZA NEW YORK", "USD", 14.75, "Dining", "Joe's Pizza NYC")
    fx_charge(76, "MTA NYCT OMNY NEW YORK", "USD", 34.00, "Transport", "MTA New York")
    fx_charge(20, "STEAMGAMES.COM", "USD", 19.99, "Entertainment", "Steam")
    b.add(b.ago(162), "visa", "FOREIGN EXCHANGE PURCHASE - PAYPAL *ALIEXPRESS", -38.17,
          "Shopping", "AliExpress")

    # Duplicate charges (same merchant, same amount, within 72h)
    b.add(today - timedelta(days=43), "visa", "UBER* EATS TORONTO ON", -34.87, "Dining", "Uber Eats")
    b.add(today - timedelta(days=43), "visa", "UBER* EATS TORONTO ON", -34.87, "Dining", "Uber Eats")
    b.add(b.ago(130), "visa", "AMAZON.CA*R72KD1 AMAZON.CA", -64.99, "Shopping", "Amazon.ca")
    b.add(b.ago(129), "visa", "AMAZON.CA*R72KD1 AMAZON.CA", -64.99, "Shopping", "Amazon.ca")

    # Bank fees
    b.add(b.ago(214), "chq", "NSF FEE - RETURNED ITEM", -48.00, "Bank Fees")
    b.add(b.ago(214), "chq", "OVERDRAFT INTEREST", -3.87, "Bank Fees")
    b.add(b.ago(174), "chq", "INTERAC E-TRANSFER FEE", -1.50, "Bank Fees")
    b.add(trip + timedelta(days=1), "chq", "FOREIGN ATM WITHDRAWAL FEE", -5.00, "Bank Fees")
    b.add(b.ago(97), "chq", "ATM FEE - OUT OF NETWORK", -3.50, "Bank Fees")
    b.add(b.ago(27), "chq", "MONTHLY FEE - PAPER STATEMENT", -2.00, "Bank Fees")

    # ── This week: a splurge (weekly spike, big-dinner anomaly, over Dining budget) ─
    b.add(today - timedelta(days=3), "visa", "MIKU TORONTO BAY ST", -186.40, "Dining", "Miku Toronto")
    b.add(today - timedelta(days=2), "visa", "SPORT CHEK EATON CENTRE", -89.99, "Shopping", "Sport Chek")
    b.add(today - timedelta(days=1), "visa", "UBER* EATS TORONTO ON", -41.23, "Dining", "Uber Eats")
    b.add(today - timedelta(days=4), "chq", "PAI NORTHERN THAI KITCHEN", -47.80, "Dining", "Pai Northern Thai")
    # First-time merchant with no merchant name on file
    b.add(today - timedelta(days=13), "chq", "SQ *KENSINGTON VINTAGE MARKET", -64.00, "Shopping")

    b.txs.sort(key=lambda t: (t.transaction_date, t.account, t.description))
    return b.txs


def validate(txs: list[SeedTx], fx_rates: dict, today: date) -> dict:
    """Run the leak detectors offline and report what they would find."""
    from leaks.duplicates import detect_duplicates
    from leaks.fees import detect_fees
    from leaks.fx import detect_fx_markup, findings_from_fx_result
    from leaks.subscriptions import detect_forgotten_subscriptions, detect_price_creep

    debits = [t for t in txs if t.amount < 0]
    found = {
        "fx": findings_from_fx_result(detect_fx_markup(debits, fx_rates, year=today.year)),
        "duplicates": detect_duplicates(debits, recurring_merchants=[]),
        "fees": detect_fees(debits, year=today.year)["findings"],
        "price_creep": detect_price_creep(debits),
        "forgotten": detect_forgotten_subscriptions(debits),
    }
    return {k: [f.get("title") for f in v] for k, v in found.items()}


_EXPECTED_CREEP = {"Price increase: Spotify", "Price increase: Rogers Wireless"}
_EXPECTED_FORGOTTEN = {"Still using GoodLife Fitness?", "Still using Crave?"}


def _check(report: dict) -> list[str]:
    problems = []
    creep = set(report["price_creep"])
    forgotten = set(report["forgotten"])
    if creep != _EXPECTED_CREEP:
        problems.append(f"price creep: expected {sorted(_EXPECTED_CREEP)}, got {sorted(creep)}")
    if forgotten != _EXPECTED_FORGOTTEN:
        problems.append(f"forgotten: expected {sorted(_EXPECTED_FORGOTTEN)}, got {sorted(forgotten)}")
    if len(report["duplicates"]) != 2:
        problems.append(f"duplicates: expected 2, got {report['duplicates']}")
    return problems


def _wipe(db, user) -> None:
    from db.models import (
        Account,
        BankConnection,
        Budget,
        LeakFinding,
        MerchantAlias,
        Notification,
        Transaction,
        TransactionEmbedding,
    )

    account_ids = [a.id for a in db.query(Account.id).filter(Account.user_id == user.id).all()]
    if account_ids:
        tx_ids = db.query(Transaction.id).filter(Transaction.account_id.in_(account_ids))
        db.query(TransactionEmbedding).filter(
            TransactionEmbedding.transaction_id.in_(tx_ids)
        ).delete(synchronize_session=False)
        db.query(Transaction).filter(Transaction.account_id.in_(account_ids)).delete(
            synchronize_session=False
        )
        db.query(Account).filter(Account.id.in_(account_ids)).delete(synchronize_session=False)
    for model in (LeakFinding, Budget, Notification, MerchantAlias, BankConnection):
        db.query(model).filter(model.user_id == user.id).delete(synchronize_session=False)
    db.commit()


def _user_settings(user, today: date) -> None:
    now = datetime.combine(today, datetime.min.time()).isoformat()

    def goal(title, target, current, deadline, notes=None, status="active", created_days=120):
        return {
            "id": str(uuid.uuid4()),
            "title": title,
            "target_amount": target,
            "current_amount": current,
            "deadline": deadline.isoformat(),
            "notes": notes,
            "created_at": (datetime.combine(today, datetime.min.time())
                           - timedelta(days=created_days)).isoformat(),
            "status": status,
            "updated_at": now,
        }

    user.goals_json = json.dumps([
        goal("iPhone 17 Pro", 1599.00, 450.00, today + timedelta(days=80),
             "Pay cash, no financing", created_days=30),
        goal("Emergency fund (3 months rent)", 3450.00, 1850.00, today + timedelta(days=210)),
        goal("Montreal trip with friends", 800.00, 220.00, today + timedelta(days=250)),
        goal("Max out TFSA this year", 7000.00, 5500.00, date(today.year, 12, 31),
             "Wealthsimple, XEQT", created_days=260),
        goal("New laptop for school", 1400.00, 1400.00, today - timedelta(days=60),
             "Bought a MacBook Air", status="completed", created_days=300),
    ])
    user.alert_prefs_json = json.dumps({"spend_alerts": True, "email_digest": False})
    user.category_rules_json = json.dumps([
        {"id": str(uuid.uuid4()), "match": "merchant_contains", "value": "uber eats", "category": "Dining"},
        {"id": str(uuid.uuid4()), "match": "merchant_contains", "value": "presto", "category": "Transport"},
        {"id": str(uuid.uuid4()), "match": "merchant_contains", "value": "goodlife", "category": "Subscriptions"},
    ])
    user.agent_profile_json = json.dumps({
        "learned_summary": (
            "Second-year York University CS student in Toronto. Pays $1,150/mo rent, "
            "funds school with OSAP and a part-time Indigo job, and interned at Shopify "
            "over the summer. Saving for an iPhone and building an emergency fund."
        ),
        "preferences": ["Prefers concrete weekly savings targets", "Uses Wealthsimple for the TFSA"],
        "risk_flags": ["Dining and Uber Eats creep up during exam season"],
        "updated_at": today.isoformat(),
    })


def _budgets(db, user) -> None:
    from db.models import Budget

    for category, limit in [("Dining", 150), ("Groceries", 350), ("Shopping", 200),
                            ("Transport", 180), ("Entertainment", 80), ("Subscriptions", 110)]:
        db.add(Budget(user_id=user.id, category=category, monthly_limit=limit))


def _notifications(db, user) -> None:
    from db.models import Notification

    for kind, severity, title, body, read in [
        ("weekly_brief", "info", "Your weekly brief is ready",
         "Spending is up this week. Open the brief to see what changed.", False),
        ("leak_found", "warning", "New money leaks found",
         "We found duplicate charges, bank fees and two subscriptions you may have forgotten.", False),
        ("tfsa", "info", "TFSA room update",
         "You've contributed $5,500 to your TFSA this year. $1,500 of room left.", False),
        ("welcome", "info", "Welcome to FinSight",
         "Your accounts are connected. Ask the advisor anything about your money.", True),
    ]:
        db.add(Notification(user_id=user.id, kind=kind, severity=severity,
                            title=title, body=body, read=read))


def _embed(db, transactions, batch_size: int = 120) -> int:
    from app.config import settings
    from rag.indexing import index_transaction_batch

    if not settings.embeddings_configured:
        print("  Embeddings not configured — skipping semantic search index.")
        return 0
    done = 0
    for start in range(0, len(transactions), batch_size):
        batch = transactions[start : start + batch_size]
        for attempt in range(6):
            try:
                done += index_transaction_batch(db, batch)
                break
            except RuntimeError as exc:
                wait = 25 * (attempt + 1)
                print(f"  Embedding batch failed ({str(exc)[:80]}); retrying in {wait}s")
                time.sleep(wait)
        else:
            print("  Giving up on embeddings; run a reindex from the Search page later.")
            return done
        print(f"  Embedded {done}/{len(transactions)}")
    return done


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Generate and validate only")
    parser.add_argument("--no-embed", action="store_true", help="Skip semantic search embeddings")
    args = parser.parse_args()

    from db.base import SessionLocal
    from db.models import Account, LeakFinding, Transaction, User
    from leaks.boc import get_rate_dict

    today = date.today()
    db = SessionLocal()
    fx_rates = get_rate_dict(db, prefer_live=False)
    txs = build_transactions(today, fx_rates)

    report = validate(txs, fx_rates, today)
    print(f"Generated {len(txs)} transactions "
          f"({txs[0].transaction_date} → {txs[-1].transaction_date})")
    print("By category:", dict(Counter(t.category for t in txs).most_common()))
    for kind, titles in report.items():
        print(f"  {kind}: {len(titles)} → {titles}")
    problems = _check(report)
    if problems:
        print("\nUnexpected leak findings:\n  " + "\n  ".join(problems))
        sys.exit(1)
    if args.dry_run:
        print("\nDry run OK — nothing written.")
        return

    user = db.query(User).filter(User.email == args.email).first()
    if not user:
        sys.exit(f"No user with email {args.email}. Log in to the app once first.")

    print(f"\nWiping financial data for {user.email} …")
    _wipe(db, user)

    accounts = {
        "chq": Account(user_id=user.id, name="RBC Advantage Banking for Students",
                       institution="RBC Royal Bank", account_type="checking"),
        "visa": Account(user_id=user.id, name="Simplii Cash Back Visa",
                        institution="Simplii Financial", account_type="credit"),
        "hisa": Account(user_id=user.id, name="RBC High Interest eSavings",
                        institution="RBC Royal Bank", account_type="savings"),
        "tfsa": Account(user_id=user.id, name="Wealthsimple TFSA",
                        institution="Wealthsimple", account_type="savings"),
    }
    db.add_all(accounts.values())
    db.flush()

    rows = [
        Transaction(
            id=t.id,
            account_id=accounts[t.account].id,
            transaction_date=t.transaction_date,
            description=t.description,
            amount=t.amount,
            category=t.category,
            merchant=t.merchant,
        )
        for t in txs
    ]
    db.add_all(rows)
    _user_settings(user, today)
    _budgets(db, user)
    _notifications(db, user)
    db.commit()
    print(f"Inserted {len(rows)} transactions across {len(accounts)} accounts.")

    from leaks.service import money_recovered_summary, scan_all_leaks, upsert_findings

    findings = upsert_findings(db, user.id, scan_all_leaks(db, user.id))
    # Mark two as already recovered so the "money recovered" card has a value.
    for row in findings:
        ev = json.loads(row.evidence_json or "{}")
        title = ev.get("title") or ""
        if row.type == "duplicate" and "Amazon" in title:
            row.status = "resolved"
        if row.type == "fee" and "NSF" in (ev.get("description") or title):
            row.status = "resolved"
    db.commit()
    print(f"Leak scan saved {len(findings)} findings: {money_recovered_summary(db, user.id)}")

    if not args.no_embed:
        print("Embedding transactions for semantic search …")
        fresh = db.query(Transaction).filter(
            Transaction.account_id.in_([a.id for a in accounts.values()])
        ).order_by(Transaction.transaction_date.desc()).all()
        _embed(db, fresh)

    _report(db, user)


def _report(db, user) -> None:
    from app.scoping import account_ids_for_user
    from insights.anomalies import detect_anomalies
    from insights.recurring import detect_recurring_charges
    from insights.runway import analyze_cash_runway
    from insights.service import build_weekly_brief
    from insights.tfsa import tfsa_contribution_status

    ids = account_ids_for_user(db, user)
    subs = detect_recurring_charges(db, account_ids=ids)
    print("\n── What the app will show ──")
    print(f"Subscriptions ({len(subs)}):", [s.get("merchant") for s in subs])
    tfsa = tfsa_contribution_status(db, account_ids=ids)
    print("TFSA:", {k: tfsa["tfsa"].get(k) for k in ("estimated_contributions", "remaining_room")})
    runway = analyze_cash_runway(db, account_ids=ids)
    print("Runway:", {k: runway.get(k) for k in ("monthly_burn", "monthly_income_estimate", "runway_months")})
    print("Anomalies:", [a["message"] for a in detect_anomalies(db, account_ids=ids)])
    brief = build_weekly_brief(db, account_ids=ids)
    print("Weekly brief headline:", brief.get("headline"))
    print("Weekly brief alerts:", [a.get("title") for a in brief.get("alerts", [])])


if __name__ == "__main__":
    main()
