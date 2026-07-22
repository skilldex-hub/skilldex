"""Fetching, caching, and searching the skilldex registry index."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx

# GitHub Pages is primary — raw.githubusercontent's CDN can pin stale variants
# for a long time, which made freshly merged entries invisible to the CLI.
DEFAULT_INDEX_URL = "https://skilldex-hub.github.io/index.json"
FALLBACK_INDEX_URL = (
    "https://raw.githubusercontent.com/skilldex-hub/skilldex-hub.github.io/main/index.json"
)
CACHE_TTL_SECONDS = 3600
CACHE_PATH = Path.home() / ".cache" / "skilldex" / "index.json"


def index_url() -> str:
    return os.environ.get("SKILLDEX_REGISTRY_URL", DEFAULT_INDEX_URL)


def fetch_index(force: bool = False) -> dict:
    """Return the registry index, using a local cache with a 1-hour TTL.

    SKILLDEX_REGISTRY_URL may point at an alternative index — either an
    https:// URL or a local file path (useful for registry development).
    """
    url = index_url()
    local = Path(url)
    if not url.startswith(("http://", "https://")) and local.exists():
        return json.loads(local.read_text(encoding="utf-8"))

    if (
        not force
        and CACHE_PATH.exists()
        and time.time() - CACHE_PATH.stat().st_mtime < CACHE_TTL_SECONDS
    ):
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass  # fall through to a fresh fetch

    try:
        response = httpx.get(url, follow_redirects=True, timeout=15)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        if url != DEFAULT_INDEX_URL:  # custom URL: no fallback, surface the error
            raise
        response = httpx.get(FALLBACK_INDEX_URL, follow_redirects=True, timeout=15)
        response.raise_for_status()
        data = response.json()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data), encoding="utf-8")
    return data


def search(index: dict, query: str, etype: str | None = None) -> list[dict]:
    """Case-insensitive all-tokens-match search over id, name, description, and tags."""
    tokens = query.lower().split()
    results = []
    for entry in index.get("entries", []):
        if etype and entry.get("type") != etype:
            continue
        haystack = " ".join(
            [
                entry.get("id", ""),
                entry.get("name", ""),
                entry.get("description", ""),
                " ".join(entry.get("tags", [])),
            ]
        ).lower()
        if all(token in haystack for token in tokens):
            results.append(entry)
    return results


def get_entry(index: dict, entry_id: str) -> dict | None:
    for entry in index.get("entries", []):
        if entry.get("id") == entry_id:
            return entry
    return None


def get_entry_fresh(index: dict, entry_id: str, refetch=fetch_index) -> dict | None:
    """Like get_entry, but on a miss refetch the index once — the local cache
    (or a CDN edge) may predate a just-merged entry."""
    entry = get_entry(index, entry_id)
    if entry is None:
        try:
            entry = get_entry(refetch(force=True), entry_id)
        except (httpx.HTTPError, json.JSONDecodeError, OSError):
            return None
    return entry
