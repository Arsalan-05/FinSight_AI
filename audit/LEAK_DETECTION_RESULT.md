# Leak detection measured against the eval persona

Measured 2026-11-15 on `main` @ `6936ca6` (v2.0.0). Read-only:
- in-memory SQLite and the bundled offline Bank of Canada rate file;
- no network, no LLM, no database writes, no commits;
- no detector code changed or tuned.

## Bottom line

| | Production code path as-is (config A) | Scan dated to the end of the fixture year (config B) |
|---|---|---|
| Planted leaks detected (of 45 real leaks) | **3** | **23** |
| Recall over the 45 real leaks | **6.7%** (3/45) | **51.1%** (23/45) |
| Recall over all 47 planted entries | 6.4% (3/47) | 48.9% (23/47) |
| Findings scored | 19 | 55 |
| False-positive findings | **16** | **36** |
| Precision | **15.8%** (3/19) | **34.5%** (19/55) |

Config A is the honest headline: what `scan_all_leaks` reports today for this data. Config B shows what the same detectors can do when the scan date matches the data (details below). Neither number is resume-ready without the caveats in the last section.

## Fixture and ground truth

- **Builder:** `build_fixture_transactions` at `backend/evals/fixtures/seed_persona.py:46` (returns `txs, planted_leaks` at line 526). Fixture year 2025 (`seed_persona.py:13`), `RNG_SEED = 42` (line 16). Loaded with `load_fixture_into_db` (`backend/evals/fixtures/load.py`).
- **Verified size:** 600 transactions and 47 planted entries. Every entry lists the `transaction_ids` it covers, so **ground truth can be matched to findings automatically**: each finding carries transaction ids in `evidence.transaction_id` or `evidence.transaction_ids`.

The 47 planted entries:

| Planted type (line) | Entries | Is it a money leak? | Detector it maps to |
|---|---|---|---|
| `fx_markup` (`:365`), one per USD Amazon purchase | 28 | yes | `leaks/fx.py` |
| `forgotten_subscription` (`:186`), GoodLife gym, **one entry per month** | 12 | yes | `leaks/subscriptions.py` `detect_forgotten_subscriptions` |
| `subscription_price_increase` (`:219`, `:231`), Spotify, Netflix | 2 | yes | `leaks/subscriptions.py` `detect_price_creep` |
| `bank_fee` (`:412` NSF; `:443` ATM, 2 transactions) | 2 | yes | `leaks/fees.py` |
| `duplicate_charge` (`:477`), Best Buy pair | 1 | yes | `leaks/duplicates.py` |
| `recurring_housing` (`:165`), monthly rent | 1 | **no**, normal rent | none |
| `adversarial_description` (`:502`), prompt-injection text | 1 | **no**, a retrieval/injection test row | none |

So the denominator for recall is **45 real leaks**. No detector is designed to find the other 2, so "x of 47" overstates the misses.

## Matching rules (fixed before running)

- **Detected:** a finding of the mapped type whose transaction ids overlap the planted entry's ids. The duplicate pair must match exactly.
- **True positive finding:** covers at least one planted transaction of the same type. Everything else is a **false positive**.
- **Excluded from precision:** yearly roll-up findings (`evidence.kind == "yearly_summary"`), because they restate the per-transaction findings. Config B produced 2 of these ("FX markup total (2025)", "Bank fees total (2025)"). "Unverifiable" FX findings would also be excluded, but there were 0.

## Config A: production path, unmodified

`leaks.service.scan_all_leaks(db, user_id)` on the loaded fixture. Same code `GET /leaks` uses; rates from `get_rate_dict(prefer_live=False)`, which falls back to the offline file.

| Detector | Planted | Detected | Findings | TP | FP | Precision |
|---|---|---|---|---|---|---|
| FX markup | 28 | 0 | 0 | 0 | 0 | n/a |
| Forgotten subscriptions | 12 | 0 | 0 | 0 | 0 | n/a |
| Price creep | 2 | 2 | 18 | 2 | 16 | 11.1% |
| Bank fees | 2 | 0 | 0 | 0 | 0 | n/a |
| Duplicates | 1 | 1 | 1 | 1 | 0 | 100% |
| **Total** | **45** | **3** | **19** | **3** | **16** | **15.8%** |

Why three detectors return nothing here:
- **FX and fees** are called with `year=date.today().year` (`backend/leaks/service.py:60,64`), which is 2026. Both skip every transaction from another year (`fx.py:79`, `fees.py:86`), and the fixture is all 2025.
- **Forgotten subscriptions** only looks back 180 days from `date.today()` (`subscriptions.py:142,152`), and no fixture transaction falls in that window.

This also means: for real users, FX and fee findings only ever cover the current calendar year.

## Config B: same detectors, scan dated 2025-12-31

The same `scan_all_leaks` call, with `date.today()` pinned to `FIXTURE_END` (2025-12-31) in `leaks.service`, `leaks.fx`, `leaks.fees`, `leaks.subscriptions` and `insights.recurring`. That makes the scan year 2025 and puts the 180-day window inside the fixture. Only the clock changes; detector logic, thresholds and parameters are untouched. I picked this date before seeing any results, as "a scan run on the last day of the fixture's year".

| Detector | Planted | Detected | Recall | Findings | TP | FP | Precision |
|---|---|---|---|---|---|---|---|
| FX markup | 28 | 12 | 42.9% | 13 | 12 | 1 | 92.3% |
| Forgotten subscriptions | 12 | 6 | 50.0% | 20 | 1 | 19 | 5.0% |
| Price creep | 2 | 2 | 100% | 18 | 2 | 16 | 11.1% |
| Bank fees | 2 | 2 | 100% | 3 | 3 | 0 | 100% |
| Duplicates | 1 | 1 | 100% | 1 | 1 | 0 | 100% |
| **Total** | **45** | **23** | **51.1%** | **55** | **19** | **36** | **34.5%** |

### Why the misses happen

**FX: 16 of 28 missed.** Output of the explainer script (appendix):
- **14 planted entries have zero or negative markup** against the reference rate the detector uses. The fixture draws each purchase's rate at random between 1.36 and 1.42 (`seed_persona.py:352`) without looking at the Bank of Canada rate. For January–March 2025 the reference rate is 1.4382, and for October–December it is 1.42 (from the 2026-01-15 sample, see below). Every planted rate below that is a purchase *cheaper* than BoC. The detector is correct not to call these markups (`fx.py:146`: "bank beat BoC — not a leak"), so these are **labelling errors in the fixture**, not detector misses.
  - Missed this way: `amazon-fx-1-0, 1-1, 2-0, 2-1, 3-0, 3-1, 3-2, 10-0, 10-1, 11-0, 11-1, 12-0, 12-1, 12-2`.
- **2 have real but tiny markups** below the detector's minimums (`min_markup_cad=0.25` **and** `min_markup_pct=0.5`, `fx.py:58-59,143`):
  - `amazon-fx-4-1`: +$0.06
  - `amazon-fx-8-0`: +$0.15
- **The other 12 planted purchases with real markup above those minimums were all detected.**

**FX reference rates are sparse.** The offline file has only 6 USDCAD points (`backend/leaks/data/boc_sample_rates.json`: 2025-01-02, 2025-06-15, then 2026). `nearest_rate` falls back to the closest date it has (`boc.py:138-144`), so October–December 2025 purchases are compared with the 2026-01-15 rate. With real daily BoC rates (what production uses once the `fx_rates` cache is filled) the FX numbers would differ. I did not fetch live rates.

**Forgotten subscriptions: "6 of 12" is a granularity artifact.** The fixture plants the gym once per month (12 entries), but the detector emits **one** finding per merchant covering only the transactions inside its 180-day window (July–December). So the GoodLife leak *was* found, but only 6 of its 12 monthly entries overlap the finding. Counting distinct leaks instead, the gym is 1 of 1 detected.

### The false positives

- **Price creep: 16 FP**, identical in both configs. It flags any merchant with 2+ debits whose latest amount is higher than its first, including ordinary variable spending: Loblaws, Metro, FreshCo, No Frills, Costco, Freshii, Chipotle, Tim Hortons, Uber Eats, Petro-Canada, Hydro One, Shoppers Drug Mart, Cineplex, Indigo, Best Buy, and "TD" ($208.51).
- **Forgotten subscriptions: 19 FP.** Any repeat merchant with no "related" activity, including:
  - Landlord (rent, $1,450)
  - RBC TFSA (savings transfers)
  - Ahmed (friend e-transfers)
  - TTC, Rogers, Hydro One
  - Netflix and Spotify (real subscriptions, but the fixture labels them as price creep, not forgotten)
  - grocery and restaurant merchants
- **FX: 1 FP.** The prompt-injection row (`description` ends in "USD 1.00", amount −$12.34) was flagged as a $10.92 FX markup.

### Distinct-leak view (secondary)

Counting each named leak once (28 FX purchases, 1 gym, 2 price increases, 2 fee leaks, 1 duplicate = 34): config A detects 3/34 (8.8%), config B detects 18/34 (52.9%). Precision does not change.

## What you can and can't claim

- **Supported (config B, with the caveat that the scan is dated to the data):**
  - Duplicate detector: 1/1, 0 false positives.
  - Fee detector: 2/2, 0 false positives.
  - FX detector: 92% precision (12/13), and every planted purchase with a real above-minimum markup was caught (12/12).
- **Not supported:** any overall "detects N% of money leaks" figure without qualification. Overall precision is 16–35% because price creep and forgotten subscriptions over-flag. Overall recall is 7% on the production path today, because of the date filters.
- **Fixture problems that affect any recall figure:**
  - 14 of the 28 FX labels aren't markups at all.
  - 2 of the 47 entries aren't leaks.
  - The gym is planted 12 times for what the detector treats as one leak.

## How it was run

Both scripts are in the session scratchpad. They are reproduced below so this file stands alone. Every Python call went through a wrapper that blanks all database and API credentials, so `db/base.py` cannot reach Supabase and no paid API key is present.

```sh
SP=<tmp-dir>
"$SP/safe.sh" -I "$SP/measure_leaks.py" A   # config A
"$SP/safe.sh" -I "$SP/measure_leaks.py" B   # config B
"$SP/safe.sh" -I "$SP/fx_explain.py"        # FX miss explanation
```

### `safe.sh`

```sh
#!/bin/sh
# Run backend python with every DB/API variable neutralised so nothing reaches Supabase or paid APIs.
cd "/Users/Arsalan Amir Ali/Developer/GitHub/FinSight_AI/backend"
exec env DATABASE_URL="postgresql://nobody:x@127.0.0.1:1/none" DATABASE_FALLBACK_URL="postgresql://nobody:x@127.0.0.1:1/none" \
 DATABASE_FALLBACK_ENABLED=false USE_SUPABASE_DB=false SUPABASE_DB_PASSWORD="" SUPABASE_POOLER_HOST="" SUPABASE_URL="" \
 SUPABASE_JWT_SECRET="" SUPABASE_SERVICE_ROLE_KEY="" ANTHROPIC_API_KEY="" GROQ_API_KEY="" VOYAGE_API_KEY="" TAVILY_API_KEY="" \
 FINNHUB_API_KEY="" PLAID_CLIENT_ID="" PLAID_SECRET="" SMTP_HOST="" OLLAMA_BASE_URL="http://127.0.0.1:1" ENVIRONMENT=test \
 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python "$@"
```

### `measure_leaks.py`

```python
"""Measure backend/leaks detectors against the eval persona fixture, in memory.

Read-only: in-memory SQLite, offline BoC sample rates, no network, no LLM, no
detector code changed. Run from backend/ via safe.sh (all DB/API env blanked).

Config A: production path, leaks.service.scan_all_leaks(db, user_id), unmodified.
Config B: same detector functions, unmodified, but called with year=FIXTURE_YEAR
          and with date.today() pinned to FIXTURE_END (2025-12-31) in the modules
          that read the clock, i.e. "scan run at the end of the fixture year".
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from collections import defaultdict

sys.path.insert(0, ".")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import db.models  # noqa: E402,F401  (register tables)
from db.base import Base  # noqa: E402
from evals.fixtures.load import load_fixture_into_db  # noqa: E402
from evals.fixtures.seed_persona import FIXTURE_END, FIXTURE_YEAR  # noqa: E402

# Planted type -> detector finding type. Non-leak planted entries map to None.
TYPE_MAP = {
    "fx_markup": "fx_markup",
    "forgotten_subscription": "forgotten_subscription",
    "subscription_price_increase": "subscription_creep",
    "bank_fee": "fee",
    "duplicate_charge": "duplicate",
    "recurring_housing": None,  # rent: not a money leak
    "adversarial_description": None,  # prompt-injection test row: not a money leak
}
DETECTOR_OF = {
    "fx_markup": "fx.py",
    "forgotten_subscription": "subscriptions.py (forgotten)",
    "subscription_creep": "subscriptions.py (price creep)",
    "fee": "fees.py",
    "duplicate": "duplicates.py",
}


def finding_tx_ids(f: dict) -> set:
    ev = f.get("evidence") or {}
    ids = set(ev.get("transaction_ids") or [])
    if ev.get("transaction_id"):
        ids.add(ev["transaction_id"])
    return {i for i in ids if i}


def is_summary(f: dict) -> bool:
    return (f.get("evidence") or {}).get("kind") == "yearly_summary"


def is_unverifiable(f: dict) -> bool:
    return bool((f.get("evidence") or {}).get("unverifiable"))


def score(findings: list[dict], planted: list[dict]) -> dict:
    real = [p for p in planted if TYPE_MAP[p["type"]] is not None]
    non_leak = [p for p in planted if TYPE_MAP[p["type"]] is None]

    scored = [f for f in findings if not is_summary(f) and not is_unverifiable(f)]
    summaries = [f for f in findings if is_summary(f)]
    unverifiable = [f for f in findings if is_unverifiable(f)]

    # Recall: planted leak detected if a same-type finding covers its tx ids.
    # Duplicates need the exact pair; every other type needs any overlap.
    per_type = defaultdict(lambda: {"planted": 0, "detected": 0, "missed_ids": []})
    for p in real:
        ftype = TYPE_MAP[p["type"]]
        pids = set(p["transaction_ids"])
        hit = False
        for f in scored:
            if f.get("type") != ftype:
                continue
            fids = finding_tx_ids(f)
            if ftype == "duplicate":
                hit = pids == fids
            else:
                hit = bool(pids & fids)
            if hit:
                break
        row = per_type[p["type"]]
        row["planted"] += 1
        row["detected"] += int(hit)
        if not hit:
            row["missed_ids"].append(p["leak_id"])

    # Precision: a finding is TP if it covers tx ids of a same-type planted leak.
    planted_ids_by_ftype = defaultdict(set)
    for p in real:
        planted_ids_by_ftype[TYPE_MAP[p["type"]]] |= set(p["transaction_ids"])
    non_leak_ids = set().union(*(set(p["transaction_ids"]) for p in non_leak))

    per_det = defaultdict(lambda: {"findings": 0, "tp": 0, "fp": 0, "fp_examples": []})
    for f in scored:
        t = f.get("type")
        fids = finding_tx_ids(f)
        d = per_det[t]
        d["findings"] += 1
        if fids & planted_ids_by_ftype[t]:
            d["tp"] += 1
        else:
            d["fp"] += 1
            d["fp_examples"].append(
                {
                    "title": f.get("title"),
                    "amount_cad": f.get("amount_cad"),
                    "touches_non_leak_plant": bool(fids & non_leak_ids),
                    "n_tx": len(fids),
                    "descriptions": (f.get("evidence") or {}).get("descriptions")
                    or [(f.get("evidence") or {}).get("description")],
                }
            )

    n_real = len(real)
    detected = sum(r["detected"] for r in per_type.values())
    tp = sum(d["tp"] for d in per_det.values())
    fp = sum(d["fp"] for d in per_det.values())
    return {
        "planted_total": len(planted),
        "planted_real_leaks": n_real,
        "planted_non_leaks": [p["leak_id"] for p in non_leak],
        "detected_real_leaks": detected,
        "recall_over_real": round(detected / n_real, 4) if n_real else None,
        "recall_over_all_47": round(detected / len(planted), 4),
        "scored_findings": len(scored),
        "tp_findings": tp,
        "fp_findings": fp,
        "precision": round(tp / (tp + fp), 4) if (tp + fp) else None,
        "summary_findings_excluded": [(f.get("type"), f.get("title")) for f in summaries],
        "unverifiable_findings_excluded": len(unverifiable),
        "per_planted_type": dict(per_type),
        "per_detector": dict(per_det),
    }


def fresh_session():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=eng)
    return sessionmaker(bind=eng)()


def run_a():
    from leaks.service import scan_all_leaks

    db = fresh_session()
    info = load_fixture_into_db(db)
    db.commit()
    user_id = info["user"].id if hasattr(info["user"], "id") else info["user"]["id"]
    findings = scan_all_leaks(db, user_id)
    return findings, info["planted_leaks"], info


def run_b():
    import insights.recurring as rec_mod
    import leaks.fees as fees_mod
    import leaks.fx as fx_mod
    import leaks.service as svc_mod
    import leaks.subscriptions as subs_mod

    class PinnedDate(_dt.date):
        @classmethod
        def today(cls):  # type: ignore[override]
            return cls(FIXTURE_END.year, FIXTURE_END.month, FIXTURE_END.day)

    for mod in (subs_mod, fx_mod, fees_mod, svc_mod, rec_mod):
        if hasattr(mod, "date"):
            mod.date = PinnedDate  # clock only; detector logic untouched

    db = fresh_session()
    info = load_fixture_into_db(db)
    db.commit()
    user_id = info["user"].id if hasattr(info["user"], "id") else info["user"]["id"]
    # scan_all_leaks passes year=date.today().year, which is now FIXTURE_YEAR.
    findings = svc_mod.scan_all_leaks(db, user_id)
    return findings, info["planted_leaks"]


if __name__ == "__main__":
    which = sys.argv[1]
    if which == "A":
        findings, planted, info = run_a()
        print("fixture keys:", sorted(info.keys()))
    else:
        findings, planted = run_b()
    print("raw findings by type:", dict(sorted(
        {t: sum(1 for f in findings if f.get("type") == t)
         for t in {f.get("type") for f in findings}}.items())))
    print(json.dumps(score(findings, planted), indent=2, default=str))
```

### `fx_explain.py`

```python
import sys; sys.path.insert(0, ".")
from evals.fixtures.seed_persona import build_fixture_transactions
from leaks.boc import load_offline_rates, nearest_rate
from leaks.fx import _pair_for
PAIR = _pair_for("USD")
rates = load_offline_rates()
usd = sorted(d for (d, p) in rates if p == PAIR)
print("offline USDCAD points:", len(usd), "range", usd[0], "->", usd[-1] if usd else None)
txs, planted = build_fixture_transactions("u", {"rbc_checking": "a", "td_credit": "b"})
by_id = {t["id"]: t for t in txs}
neg = pos_small = flagged = 0
for p in planted:
    if p["type"] != "fx_markup": continue
    t = by_id[p["transaction_ids"][0]]
    boc = nearest_rate(rates, t["transaction_date"], PAIR)
    implied = abs(t["amount"]) / p["usd_amount"]
    markup = abs(t["amount"]) - p["usd_amount"] * boc
    status = "markup<=0" if markup <= 0 else "markup>0"
    print(f'{p["leak_id"]:16} {t["transaction_date"]} implied={implied:.4f} boc={boc:.4f} markup_cad={markup:+.2f} {status}')
```

### Raw output

Config A, first line: `raw findings by type: {'duplicate': 1, 'subscription_creep': 18}`

Config B, first line: `raw findings by type: {'duplicate': 1, 'fee': 4, 'forgotten_subscription': 20, 'fx_markup': 14, 'subscription_creep': 18}`. The 4 fee findings are 3 per-transaction + 1 yearly summary, and the 14 FX findings are 13 per-transaction + 1 yearly summary.

FX explainer output:

```
offline USDCAD points: 6 range 2025-01-02 -> 2026-09-01
amazon-fx-1-0    2025-01-05 implied=1.3795 boc=1.4382 markup_cad=-2.05 markup<=0
amazon-fx-1-1    2025-01-14 implied=1.3634 boc=1.4382 markup_cad=-5.77 markup<=0
amazon-fx-2-0    2025-02-05 implied=1.3641 boc=1.4382 markup_cad=-4.11 markup<=0
amazon-fx-2-1    2025-02-14 implied=1.4059 boc=1.4382 markup_cad=-2.47 markup<=0
amazon-fx-3-0    2025-03-05 implied=1.3657 boc=1.4382 markup_cad=-1.39 markup<=0
amazon-fx-3-1    2025-03-14 implied=1.3742 boc=1.4382 markup_cad=-4.86 markup<=0
amazon-fx-3-2    2025-03-23 implied=1.3889 boc=1.4382 markup_cad=-2.43 markup<=0
amazon-fx-4-0    2025-04-05 implied=1.4163 boc=1.3650 markup_cad=+3.55 markup>0
amazon-fx-4-1    2025-04-14 implied=1.3670 boc=1.3650 markup_cad=+0.06 markup>0
amazon-fx-5-0    2025-05-05 implied=1.3995 boc=1.3650 markup_cad=+1.21 markup>0
amazon-fx-5-1    2025-05-14 implied=1.3767 boc=1.3650 markup_cad=+0.57 markup>0
amazon-fx-6-0    2025-06-05 implied=1.3747 boc=1.3650 markup_cad=+0.19 markup>0
amazon-fx-6-1    2025-06-14 implied=1.4111 boc=1.3650 markup_cad=+2.51 markup>0
amazon-fx-6-2    2025-06-23 implied=1.3850 boc=1.3650 markup_cad=+0.47 markup>0
amazon-fx-7-0    2025-07-05 implied=1.4101 boc=1.3650 markup_cad=+3.91 markup>0
amazon-fx-7-1    2025-07-14 implied=1.4041 boc=1.3650 markup_cad=+2.32 markup>0
amazon-fx-8-0    2025-08-05 implied=1.3673 boc=1.3650 markup_cad=+0.15 markup>0
amazon-fx-8-1    2025-08-14 implied=1.4070 boc=1.3650 markup_cad=+3.94 markup>0
amazon-fx-9-0    2025-09-05 implied=1.3784 boc=1.3650 markup_cad=+0.71 markup>0
amazon-fx-9-1    2025-09-14 implied=1.4034 boc=1.3650 markup_cad=+1.37 markup>0
amazon-fx-9-2    2025-09-23 implied=1.4045 boc=1.3650 markup_cad=+1.67 markup>0
amazon-fx-10-0   2025-10-05 implied=1.3774 boc=1.4200 markup_cad=-2.71 markup<=0
amazon-fx-10-1   2025-10-14 implied=1.4023 boc=1.4200 markup_cad=-0.63 markup<=0
amazon-fx-11-0   2025-11-05 implied=1.3877 boc=1.4200 markup_cad=-2.74 markup<=0
amazon-fx-11-1   2025-11-14 implied=1.3911 boc=1.4200 markup_cad=-0.64 markup<=0
amazon-fx-12-0   2025-12-05 implied=1.3898 boc=1.4200 markup_cad=-2.83 markup<=0
amazon-fx-12-1   2025-12-14 implied=1.3899 boc=1.4200 markup_cad=-0.63 markup<=0
amazon-fx-12-2   2025-12-23 implied=1.4122 boc=1.4200 markup_cad=-0.49 markup<=0
```
