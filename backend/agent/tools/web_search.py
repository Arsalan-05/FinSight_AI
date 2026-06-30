"""Live web search for financial context — Tavily (preferred) or DuckDuckGo fallback."""

from __future__ import annotations

import json
import re
from html import unescape
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen

from app.config import settings

_USER_AGENT = "FinSightAI/1.2 (finance-agent; +https://github.com)"
_DDG_HTML = "https://html.duckduckgo.com/html/"
_TAVILY_URL = "https://api.tavily.com/search"


def _fetch_text(url: str, *, data: bytes | None = None, timeout: float = 12.0) -> str:
    headers = {"User-Agent": _USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urlopen(req, timeout=timeout) as resp:
        raw: bytes = resp.read()
        return raw.decode("utf-8", errors="replace")


def _search_tavily(query: str, max_results: int) -> list[dict[str, Any]] | None:
    key = settings.tavily_api_key.strip()
    if not key:
        return None
    payload = json.dumps(
        {
            "api_key": key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True,
        }
    ).encode()
    try:
        req = Request(
            _TAVILY_URL,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": _USER_AGENT},
            method="POST",
        )
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    results: list[dict[str, Any]] = []
    answer = data.get("answer")
    if answer:
        results.append(
            {
                "title": "Tavily summary",
                "snippet": str(answer),
                "url": "",
                "source": "tavily",
            }
        )
    for item in data.get("results", [])[:max_results]:
        results.append(
            {
                "title": item.get("title", ""),
                "snippet": item.get("content", ""),
                "url": item.get("url", ""),
                "source": "tavily",
            }
        )
    return results or None


def _search_duckduckgo(query: str, max_results: int) -> list[dict[str, Any]]:
    body = urlencode({"q": query, "b": "", "kl": ""}).encode()
    try:
        html = _fetch_text(_DDG_HTML, data=body)
    except (HTTPError, URLError, TimeoutError) as exc:
        return [{"error": f"Web search unavailable: {exc.__class__.__name__}"}]

    # DuckDuckGo HTML lite result blocks
    blocks = re.findall(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'class="result__snippet"[^>]*>(.*?)</(?:a|td|span)',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    results: list[dict[str, Any]] = []
    for url, title_raw, snippet_raw in blocks[:max_results]:
        title = unescape(re.sub(r"<[^>]+>", "", title_raw)).strip()
        snippet = unescape(re.sub(r"<[^>]+>", "", snippet_raw)).strip()
        if title or snippet:
            results.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "url": unescape(url),
                    "source": "duckduckgo",
                }
            )

    if not results:
        # Instant-answer API fallback for factual queries
        instant_url = (
            f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
        )
        try:
            with urlopen(
                Request(instant_url, headers={"User-Agent": _USER_AGENT}),
                timeout=8,
            ) as resp:
                instant = json.loads(resp.read().decode())
            abstract = instant.get("AbstractText") or instant.get("Answer") or ""
            if abstract:
                results.append(
                    {
                        "title": instant.get("Heading") or query,
                        "snippet": abstract,
                        "url": instant.get("AbstractURL") or "",
                        "source": "duckduckgo_instant",
                    }
                )
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            pass

    if not results:
        return [{"error": f"No web results found for: {query}"}]
    return results


def search_web(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web for current rates, tax rules, product info, or general finance context."""
    q = query.strip()
    if not q:
        return {"error": "Query is required.", "results": []}
    if not settings.web_search_enabled:
        return {"error": "Web search is disabled.", "results": []}

    limit = max(1, min(max_results, 8))
    tavily = _search_tavily(q, limit)
    if tavily:
        return {"query": q, "results": tavily, "provider": "tavily", "count": len(tavily)}

    ddg = _search_duckduckgo(q, limit)
    has_error = ddg and ddg[0].get("error")
    return {
        "query": q,
        "results": ddg,
        "provider": "duckduckgo",
        "count": 0 if has_error else len(ddg),
    }
