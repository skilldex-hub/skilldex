import json

import httpx

from skilldex.registry import fetch_index, get_entry, get_entry_fresh, search

INDEX = {
    "entries": [
        {
            "id": "pdf",
            "type": "skill",
            "name": "PDF Toolkit",
            "description": "Extract text and tables from PDF files",
            "tags": ["documents"],
        },
        {
            "id": "fetch",
            "type": "mcp",
            "name": "Fetch",
            "description": "Fetch web pages as markdown",
            "tags": ["web", "http"],
        },
    ]
}


def test_search_matches_description():
    assert [e["id"] for e in search(INDEX, "tables")] == ["pdf"]


def test_search_matches_tags():
    assert [e["id"] for e in search(INDEX, "http")] == ["fetch"]


def test_search_all_tokens_must_match():
    assert search(INDEX, "pdf web") == []


def test_search_type_filter():
    assert [e["id"] for e in search(INDEX, "f", etype="mcp")] == ["fetch"]


def test_get_entry():
    assert get_entry(INDEX, "pdf")["name"] == "PDF Toolkit"
    assert get_entry(INDEX, "nope") is None


def test_get_entry_fresh_hit_needs_no_refetch():
    def boom(force=False):
        raise AssertionError("should not refetch on a hit")

    assert get_entry_fresh(INDEX, "pdf", refetch=boom)["name"] == "PDF Toolkit"


def test_get_entry_fresh_refetches_on_miss():
    fresh = {"entries": INDEX["entries"] + [{"id": "brand-new", "type": "skill", "name": "New"}]}
    assert get_entry_fresh(INDEX, "brand-new", refetch=lambda force: fresh)["name"] == "New"


def test_get_entry_fresh_miss_with_failing_refetch():
    def fail(force=False):
        raise httpx.ConnectError("offline")

    assert get_entry_fresh(INDEX, "nope", refetch=fail) is None


def test_fetch_index_local_path(tmp_path, monkeypatch):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(INDEX))
    monkeypatch.setenv("SKILLDEX_REGISTRY_URL", str(index_file))
    assert fetch_index() == INDEX
