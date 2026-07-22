"""Install skills/agents from GitHub and MCP servers into .mcp.json."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import httpx

MCP_SERVER_KEYS = ("type", "command", "args", "env", "url", "headers")


def skill_dest(project: bool) -> Path:
    base = Path.cwd() if project else Path.home()
    return base / ".claude" / "skills"


def agent_dest(project: bool) -> Path:
    base = Path.cwd() if project else Path.home()
    return base / ".claude" / "agents"


def install_source(entry: dict, dest_root: Path) -> Path:
    """Download the entry's source directory into dest_root/<id>.

    Fetches the repo tarball from codeload.github.com — unlike the GitHub
    contents API this is not rate-limited, so installs keep working from
    shared IPs and CI.
    """
    source = entry["source"]
    ref = source.get("ref") or "HEAD"
    url = f"https://codeload.github.com/{source['repo']}/tar.gz/{ref}"
    response = httpx.get(url, follow_redirects=True, timeout=120)
    response.raise_for_status()
    dest = dest_root / entry["id"]
    extracted = extract_subdir(response.content, source.get("path", ""), dest)
    if extracted == 0:
        raise FileNotFoundError(
            f"path {source.get('path')!r} not found in {source['repo']}@{ref}"
        )
    return dest


def extract_subdir(tar_bytes: bytes, path: str, dest: Path) -> int:
    """Extract files under `path` (relative to repo root) from a GitHub
    tarball into dest, stripping the leading archive directory. Returns the
    number of files written."""
    prefix = path.strip("/")
    if prefix == ".":
        prefix = ""
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()
    written = 0
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            parts = member.name.split("/", 1)  # "<repo>-<ref>/<relpath>"
            if len(parts) < 2:
                continue
            rel = parts[1]
            if prefix:
                if not (rel == prefix or rel.startswith(prefix + "/")):
                    continue
                rel = rel[len(prefix) :].lstrip("/")
            if not rel:
                continue
            target = dest / rel
            if not target.resolve().is_relative_to(dest_resolved):
                continue  # path traversal guard
            target.parent.mkdir(parents=True, exist_ok=True)
            fileobj = tar.extractfile(member)
            if fileobj is None:
                continue
            target.write_bytes(fileobj.read())
            written += 1
    return written


def user_mcp_config() -> Path:
    """Claude Code's user-wide config — servers here load in every session."""
    return Path.home() / ".claude.json"


def install_mcp(entry: dict, config_path: Path | None = None) -> Path:
    """Merge the entry's MCP server definition into an MCP config file.

    Defaults to the project's ./.mcp.json; pass user_mcp_config() for a
    user-wide install. Other keys in the target file are preserved.
    """
    config_path = config_path or Path.cwd() / ".mcp.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    servers = config.setdefault("mcpServers", {})
    mcp = entry["mcp"]
    servers[entry["id"]] = {key: mcp[key] for key in MCP_SERVER_KEYS if mcp.get(key)}
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config_path
