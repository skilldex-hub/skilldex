"""Install skills/agents from GitHub and MCP servers into .mcp.json."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

GITHUB_API = "https://api.github.com"

MCP_SERVER_KEYS = ("type", "command", "args", "env", "url", "headers")


def skill_dest(project: bool) -> Path:
    base = Path.cwd() if project else Path.home()
    return base / ".claude" / "skills"


def agent_dest(project: bool) -> Path:
    base = Path.cwd() if project else Path.home()
    return base / ".claude" / "agents"


def install_source(entry: dict, dest_root: Path) -> Path:
    """Download the entry's source directory from GitHub into dest_root/<id>."""
    source = entry["source"]
    dest = dest_root / entry["id"]
    dest.mkdir(parents=True, exist_ok=True)
    _download_dir(source["repo"], source["path"], source.get("ref"), dest)
    return dest


def _list_contents(repo: str, path: str, ref: str | None) -> list[dict]:
    response = httpx.get(
        f"{GITHUB_API}/repos/{repo}/contents/{path}",
        params={"ref": ref} if ref else None,
        headers={"Accept": "application/vnd.github+json"},
        follow_redirects=True,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else [data]


def _download_dir(repo: str, path: str, ref: str | None, dest: Path) -> None:
    for item in _list_contents(repo, path, ref):
        if item["type"] == "dir":
            subdir = dest / item["name"]
            subdir.mkdir(exist_ok=True)
            _download_dir(repo, item["path"], ref, subdir)
        elif item["type"] == "file" and item.get("download_url"):
            response = httpx.get(item["download_url"], follow_redirects=True, timeout=30)
            response.raise_for_status()
            (dest / item["name"]).write_bytes(response.content)


def install_mcp(entry: dict, config_path: Path | None = None) -> Path:
    """Merge the entry's MCP server definition into the project's .mcp.json."""
    config_path = config_path or Path.cwd() / ".mcp.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    servers = config.setdefault("mcpServers", {})
    mcp = entry["mcp"]
    servers[entry["id"]] = {key: mcp[key] for key in MCP_SERVER_KEYS if mcp.get(key)}
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config_path
