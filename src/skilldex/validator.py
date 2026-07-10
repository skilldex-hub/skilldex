"""Validation for registry entries, SKILL.md files, and subagent definition files."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ENTRY_TYPES = {"skill", "agent", "mcp"}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REPO_RE = re.compile(r"^[\w.-]+/[\w.-]+$")

REQUIRED_COMMON = ("id", "type", "name", "description")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_BODY_WORDS = 5000

# Common credential shapes: OpenAI/Anthropic-style keys, GitHub tokens, Slack tokens,
# AWS access keys, and JWTs.
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|AKIA[A-Z0-9]{12,}"
    r"|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{5,})"
)

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


def looks_like_secret(value: object) -> bool:
    return isinstance(value, str) and bool(SECRET_RE.search(value))


def parse_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split a markdown document into (frontmatter dict, body).

    Returns (None, text) when there is no frontmatter block.
    Raises ValueError on malformed YAML or a non-mapping frontmatter.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML frontmatter: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return data, match.group(2)


def validate_entry(entry: dict, *, filename: str | None = None) -> list[str]:
    """Validate a skilldex registry entry. Returns a list of error strings."""
    errors: list[str] = []
    for field in REQUIRED_COMMON:
        if not entry.get(field):
            errors.append(f"missing required field: {field}")

    etype = entry.get("type")
    if etype and etype not in ENTRY_TYPES:
        errors.append(f"invalid type {etype!r}, must be one of: {', '.join(sorted(ENTRY_TYPES))}")

    eid = entry.get("id")
    if eid:
        if not ID_RE.match(str(eid)):
            errors.append(f"id {eid!r} must be kebab-case (lowercase letters, digits, hyphens)")
        if filename and Path(filename).stem != eid:
            errors.append(f"id {eid!r} must match filename {Path(filename).name!r}")

    description = entry.get("description") or ""
    if len(description) > MAX_DESCRIPTION:
        errors.append(f"description longer than {MAX_DESCRIPTION} characters")

    tags = entry.get("tags")
    if tags is not None and not (isinstance(tags, list) and all(isinstance(t, str) for t in tags)):
        errors.append("tags must be a list of strings")

    if etype in ("skill", "agent"):
        source = entry.get("source") or {}
        repo = source.get("repo")
        if not repo:
            errors.append(f"{etype} entries need source.repo ('owner/repo')")
        elif not REPO_RE.match(repo):
            errors.append(f"source.repo {repo!r} must look like 'owner/repo'")
        if not source.get("path"):
            errors.append(f"{etype} entries need source.path (directory within the repo)")

    if etype == "mcp":
        mcp = entry.get("mcp") or {}
        transport = mcp.get("type", "stdio")
        if transport == "stdio":
            if not mcp.get("command"):
                errors.append("mcp stdio entries need mcp.command")
        elif transport in ("http", "sse"):
            if not mcp.get("url"):
                errors.append(f"mcp {transport} entries need mcp.url")
        else:
            errors.append(f"mcp.type {transport!r} must be stdio, http, or sse")
        for key, value in (mcp.get("env") or {}).items():
            if looks_like_secret(value):
                errors.append(
                    f"mcp.env.{key} looks like a hardcoded secret — use a ${{VAR}} placeholder"
                )

    return errors


def validate_skill_md(path: Path) -> list[str]:
    """Validate a Claude Code SKILL.md file. Returns hard errors only."""
    return check_skill_md(path)[0]


def check_skill_md(path: Path) -> tuple[list[str], list[str]]:
    """Full SKILL.md check. Returns (errors, warnings).

    Errors break the skill (Claude won't load or trigger it correctly);
    warnings are best-practice advice.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"cannot read file: {exc}"], []
    try:
        frontmatter, body = parse_frontmatter(text)
    except ValueError as exc:
        return [str(exc)], []
    if frontmatter is None:
        return ["missing YAML frontmatter ('---' block) at the top of SKILL.md"], []

    errors: list[str] = []
    warnings: list[str] = []
    name = frontmatter.get("name")
    if not name:
        errors.append("frontmatter missing 'name'")
    else:
        name = str(name)
        if not ID_RE.match(name):
            errors.append(f"name {name!r} should be kebab-case")
        if len(name) > MAX_NAME:
            errors.append(f"name longer than {MAX_NAME} characters")

    description = frontmatter.get("description")
    if not description:
        errors.append(
            "frontmatter missing 'description' — Claude uses it to decide when to load the skill"
        )
    elif len(str(description)) > MAX_DESCRIPTION:
        errors.append(f"description longer than {MAX_DESCRIPTION} characters")

    if not body.strip():
        errors.append("SKILL.md body is empty")
    elif len(body.split()) > MAX_BODY_WORDS:
        warnings.append(
            f"body over {MAX_BODY_WORDS} words — consider moving details into files "
            "the skill references"
        )
    return errors, warnings


def validate_agent_md(path: Path) -> list[str]:
    """Validate a Claude Code subagent definition (.md with frontmatter)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"cannot read file: {exc}"]
    try:
        frontmatter, body = parse_frontmatter(text)
    except ValueError as exc:
        return [str(exc)]
    if frontmatter is None:
        return ["missing YAML frontmatter ('---' block) at the top of the agent file"]

    errors: list[str] = []
    if not frontmatter.get("name"):
        errors.append("frontmatter missing 'name'")
    if not frontmatter.get("description"):
        errors.append(
            "frontmatter missing 'description' — Claude uses it to decide when to delegate"
        )
    if not body.strip():
        errors.append("agent file has no system prompt body")
    return errors
