"""Audit local Claude Code configuration for common problems."""

from __future__ import annotations

import json
from pathlib import Path

from .validator import looks_like_secret, validate_agent_md, validate_skill_md


def audit(project_root: Path | None = None, home: Path | None = None) -> list[tuple[str, str]]:
    """Scan local Claude Code config. Returns (path, problem) findings."""
    root = project_root or Path.cwd()
    home = home or Path.home()
    findings: list[tuple[str, str]] = []

    mcp_file = root / ".mcp.json"
    if mcp_file.exists():
        findings.extend(_audit_mcp_config(mcp_file))

    for skills_dir in (home / ".claude" / "skills", root / ".claude" / "skills"):
        if skills_dir.is_dir():
            for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
                findings.extend((str(skill_md), error) for error in validate_skill_md(skill_md))

    for agents_dir in (home / ".claude" / "agents", root / ".claude" / "agents"):
        if agents_dir.is_dir():
            for agent_md in sorted(agents_dir.rglob("*.md")):
                findings.extend((str(agent_md), error) for error in validate_agent_md(agent_md))

    return findings


def _audit_mcp_config(mcp_file: Path) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    try:
        config = json.loads(mcp_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [(str(mcp_file), f"cannot parse: {exc}")]
    for name, server in (config.get("mcpServers") or {}).items():
        if not isinstance(server, dict):
            findings.append((str(mcp_file), f"server {name!r}: definition is not an object"))
            continue
        for key, value in (server.get("env") or {}).items():
            if looks_like_secret(value):
                findings.append(
                    (
                        str(mcp_file),
                        f"server {name!r}: env {key} contains what looks like a plaintext "
                        "secret — .mcp.json is usually committed; use a ${VAR} placeholder",
                    )
                )
        for header, value in (server.get("headers") or {}).items():
            if looks_like_secret(value):
                findings.append(
                    (
                        str(mcp_file),
                        f"server {name!r}: header {header} contains what looks like a "
                        "plaintext secret — use a ${VAR} placeholder",
                    )
                )
    return findings
