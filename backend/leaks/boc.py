"""Bank of Canada Valet FX rate fetch/cache with offline fallback."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import URLError
from urllib.request import urlopen

from sqlalchemy.orm import Session

from db.models import FxRate

logger = logging.getLogger(__name__)

_BOC_SERIES = "FXUSDCAD,FXEURCAD,FXGBPCAD"
_BOC_URL = f"https://www.bankofcanada.ca/valet/observations/{_BOC_SERIES}/json"
_SAMPLE_PATH = Path(__file__).resolve().parent / "data" / "boc_sample_rates.json"

RateKey = Tuple[date, str]
RateDict = Dict[RateKey, float]


def load_offline_rates() -> RateDict:
    """Load bundled sample BoC rates (offline / test fallback)."""
    with open(_SAMPLE_PATH, encoding="utf-8") as fh:
        payload = json.load(fh)
    out: RateDict = {}
    for row in payload.get("rates", []):
        d = date.fromisoformat(str(row["date"]))
        pair = str(row["pair"]).upper().replace("/", "")
        out[(d, pair)] = float(row["rate"])
    return out


def fetch_boc_observations(*, start_date: Optional[date] = None) -> list[dict[str, Any]]:
    """Fetch raw Valet observations; returns [] on network/parse failure."""
    url = _BOC_URL
    if start_date is not None:
        url = f"{_BOC_URL}?start_date={start_date.isoformat()}"
    try:
        with urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.warning("BoC Valet unavailable: %s", exc)
        return []
    return list(data.get("observations") or [])


def observations_to_rate_dict(observations: list[dict[str, Any]]) -> RateDict:
    """Convert Valet observation rows into {(date, pair): rate}."""
    out: RateDict = {}
    for obs in observations:
        raw_d = obs.get("d")
        if not raw_d:
            continue
        d = date.fromisoformat(str(raw_d))
        for key, val in obs.items():
            if not key.startswith("FX") or not isinstance(val, dict) or "v" not in val:
                continue
            pair = key.replace("FX", "", 1).upper()
            try:
                out[(d, pair)] = float(val["v"])
            except (TypeError, ValueError):
                continue
    return out


def cache_rates_to_db(db: Session, rates: RateDict, *, source: str = "bank_of_canada") -> int:
    """Upsert rates into fx_rates. Returns number of rows written/updated."""
    written = 0
    for (d, pair), rate in rates.items():
        existing = db.get(FxRate, {"date": d, "pair": pair})
        if existing is None:
            db.add(FxRate(date=d, pair=pair, rate=rate, source=source))
            written += 1
        else:
            existing.rate = rate
            existing.source = source
            written += 1
    db.commit()
    return written


def rates_from_db(db: Session) -> RateDict:
    """Load all cached FX rates from the database."""
    out: RateDict = {}
    for row in db.query(FxRate).all():
        out[(row.date, row.pair.upper())] = float(row.rate)
    return out


def get_rate_dict(
    db: Optional[Session] = None,
    *,
    prefer_live: bool = True,
    start_date: Optional[date] = None,
) -> RateDict:
    """
    Resolve a {(date, pair): rate} map.

    Order: live Valet (optional) → DB cache → offline sample file.
    """
    if prefer_live:
        live = observations_to_rate_dict(fetch_boc_observations(start_date=start_date))
        if live:
            if db is not None:
                try:
                    cache_rates_to_db(db, live, source="bank_of_canada")
                except Exception as exc:  # noqa: BLE001 — cache must not break callers
                    logger.warning("Failed to cache BoC rates: %s", exc)
            return live

    if db is not None:
        cached = rates_from_db(db)
        if cached:
            return cached

    return load_offline_rates()


def nearest_rate(
    rates: RateDict,
    on: date,
    pair: str,
    *,
    max_lookback_days: int = 7,
) -> Optional[float]:
    """Find rate for pair on `on`, walking back up to max_lookback_days for weekends/holidays."""
    pair_u = pair.upper().replace("/", "")
    for offset in range(max_lookback_days + 1):
        d = date.fromordinal(on.toordinal() - offset)
        if (d, pair_u) in rates:
            return rates[(d, pair_u)]
    # Fall back to any date for this pair (sample file may be sparse)
    candidates = [(d, r) for (d, p), r in rates.items() if p == pair_u]
    if not candidates:
        return None
    candidates.sort(key=lambda x: abs((x[0] - on).days))
    return candidates[0][1]


def refresh_boc_cache(db: Session, *, start_date: Optional[date] = None) -> dict[str, Any]:
    """Background-friendly refresh: live fetch with offline seed if Valet is down."""
    live = observations_to_rate_dict(
        fetch_boc_observations(start_date=start_date or date(datetime.utcnow().year, 1, 1))
    )
    if live:
        n = cache_rates_to_db(db, live, source="bank_of_canada")
        return {"source": "bank_of_canada", "cached": n}
    offline = load_offline_rates()
    n = cache_rates_to_db(db, offline, source="offline_fallback")
    return {"source": "offline_fallback", "cached": n}
