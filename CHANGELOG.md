# Changelog

## 0.1.0 — unreleased

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
