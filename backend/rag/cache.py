"""Per-user in-memory semantic cache for retrieval; invalidated on note edits."""

from __future__ import annotations

import hashlib
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _fingerprint(vector: list[float], *, dims: int = 16) -> str:
    """Cheap fingerprint for exact-key lookups (not full cosine)."""
    sample = vector[:dims] if len(vector) >= dims else vector
    raw = ",".join(f"{v:.4f}" for v in sample)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


@dataclass
class CacheEntry:
    query_vector: list[float]
    query_text: str
    payload: Any
    created_at: float = field(default_factory=time.time)


class SemanticCache:
    """In-memory per-user semantic cache.

    Lookup prefers exact fingerprint match, then cosine similarity ≥ threshold
    against stored query vectors for that user.
    """

    def __init__(self, *, similarity_threshold: float = 0.97, max_entries_per_user: int = 64) -> None:
        self.similarity_threshold = similarity_threshold
        self.max_entries_per_user = max_entries_per_user
        self._store: dict[str, dict[str, CacheEntry]] = {}
        self._lock = threading.Lock()

    def get(
        self,
        user_key: str,
        query_vector: list[float],
        *,
        query_text: str = "",
    ) -> Any | None:
        with self._lock:
            bucket = self._store.get(user_key)
            if not bucket:
                return None
            fp = _fingerprint(query_vector)
            if fp in bucket:
                return bucket[fp].payload
            best_sim = -1.0
            best_payload: Any = None
            for entry in bucket.values():
                sim = _cosine(query_vector, entry.query_vector)
                if sim > best_sim:
                    best_sim = sim
                    best_payload = entry.payload
            if best_sim >= self.similarity_threshold:
                return best_payload
            # Exact text fallback when vectors unavailable / stubbed
            if query_text:
                for entry in bucket.values():
                    if entry.query_text == query_text:
                        return entry.payload
            return None

    def set(
        self,
        user_key: str,
        query_vector: list[float],
        payload: Any,
        *,
        query_text: str = "",
    ) -> None:
        with self._lock:
            bucket = self._store.setdefault(user_key, {})
            fp = _fingerprint(query_vector) if query_vector else hashlib.sha256(
                query_text.encode()
            ).hexdigest()[:24]
            bucket[fp] = CacheEntry(
                query_vector=list(query_vector),
                query_text=query_text,
                payload=payload,
            )
            if len(bucket) > self.max_entries_per_user:
                # Drop oldest
                oldest_key = min(bucket.items(), key=lambda kv: kv[1].created_at)[0]
                del bucket[oldest_key]

    def invalidate(self, user_key: str) -> None:
        """Drop all cached retrievals for *user_key* (call on note edits)."""
        with self._lock:
            self._store.pop(user_key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Process-wide cache instance
semantic_cache = SemanticCache()


def cache_user_key(user_id: str | None, account_ids: list[str] | None) -> str:
    """Stable cache partition key for a retrieval scope."""
    if user_id:
        return f"user:{user_id}"
    if account_ids:
        return "accounts:" + ",".join(sorted(account_ids))
    return "anon"
