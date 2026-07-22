# skilldex

[![CI](https://github.com/skilldex-hub/skilldex/actions/workflows/ci.yml/badge.svg)](https://github.com/skilldex-hub/skilldex/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/skilldex)](https://pypi.org/project/skilldex/)
[![Downloads](https://img.shields.io/pypi/dm/skilldex)](https://pypi.org/project/skilldex/)

**Search, install, validate, and audit Claude Code skills, subagents, and MCP servers — from one community registry.**

Claude Code extensions live scattered across hundreds of repos. skilldex gives you a package-manager-style workflow for all three extension types:

```bash
# no install needed (uvx ships with uv — brew install uv)
uvx skilldex search pdf
uvx skilldex install pdf              # → ~/.claude/skills/pdf
uvx skilldex install fetch            # MCP server → ./.mcp.json
uvx skilldex install code-reviewer -p # subagent → ./.claude/agents (project scope)
```

Entries come from the community-maintained [skilldex-registry](https://github.com/skilldex-hub/skilldex-hub.github.io) — every entry is CI-validated before it's merged. Browse it in your browser at [skilldex-hub.github.io](https://skilldex-hub.github.io/).

## Install

```bash
pip install skilldex        # or: uv tool install skilldex
```

## Commands

| Command | What it does |
|---|---|
| `skilldex search <query> [-t skill\|agent\|mcp]` | Search the registry |
| `skilldex show <id>` | Full registry entry as JSON |
| `skilldex install <id> [--project]` | Install a skill/agent (user or project scope) or add an MCP server to `.mcp.json` |
| `skilldex list` | Everything installed locally |
| `skilldex validate <path>` | Lint a `SKILL.md`, subagent `.md`, or registry entry `.json` |
| `skilldex audit` | Scan local Claude Code config for problems (broken frontmatter, plaintext secrets in `.mcp.json`, …) |

## Why validate/audit?

- A skill with a bad `description` silently never triggers — `validate` catches the common frontmatter mistakes before you wonder why.
- `.mcp.json` is usually committed to git; `audit` flags API keys pasted where a `${VAR}` placeholder belongs.

## Registry

Want your skill, subagent, or MCP server listed? Open a PR adding one JSON file to
[skilldex-registry](https://github.com/skilldex-hub/skilldex-hub.github.io) — CI validates it automatically,
and `skilldex validate` runs the same checks locally.

Point the CLI at a different (or local) index with `SKILLDEX_REGISTRY_URL`.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

MIT licensed. Not affiliated with Anthropic.
