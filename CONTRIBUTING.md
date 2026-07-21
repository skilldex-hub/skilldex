# Contributing to skilldex

PRs welcome — this project is intentionally small and readable.

## Setup

```bash
git clone https://github.com/drewn-ed/skilldex
cd skilldex
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"   # plain `pip install .` also works
.venv/bin/pytest                     # tests run straight from src/
.venv/bin/ruff check .
```

## Layout

| File | What it does |
|---|---|
| `src/skilldex/cli.py` | Typer commands, Rich output |
| `src/skilldex/registry.py` | index fetch/cache/search |
| `src/skilldex/installer.py` | GitHub downloads, `.mcp.json` merging |
| `src/skilldex/validator.py` | all validation rules + secret detection |
| `src/skilldex/audit.py` | local config scanning |

## Ground rules

- Every behavior change comes with a test.
- `ruff check .` and `pytest` must pass (CI runs them on 3.10/3.12/3.13).
- Keep dependencies minimal — currently typer, rich, httpx, pyyaml.
- Want to list your skill/agent/MCP server? That PR goes to
  [skilldex-registry](https://github.com/drewn-ed/skilldex-registry), not here.
