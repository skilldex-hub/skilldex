# Changelog

## 0.1.1 — 2026-07-21

- Project moved to the skilldex-hub organization: registry now lives at
  https://skilldex-hub.github.io/ and the default index URL points there.
- New `skilldex install <id> --global` for MCP servers: registers the server
  user-wide (in `~/.claude.json`) so it loads in every session, instead of
  only the current project's `.mcp.json`.

## 0.1.0 — 2026-07-21

Initial release.

- `skilldex search / show` — query the community registry of Claude Code skills,
  subagents, and MCP servers
- `skilldex install <id> [--project]` — install skills into `~/.claude/skills`
  (or `./.claude`), subagents into `agents/`, MCP servers into `./.mcp.json`
- `skilldex list` — everything installed locally
- `skilldex validate` — lint SKILL.md files, subagent files, and registry entries
- `skilldex audit` — scan local Claude Code config for broken frontmatter and
  plaintext secrets in `.mcp.json`
- Registry index served from GitHub Pages with CDN-stale fallback and
  refetch-on-miss, cached locally for 1 hour (`--refresh` to bypass,
  `SKILLDEX_REGISTRY_URL` to override)
