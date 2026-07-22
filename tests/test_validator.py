from pathlib import Path

from skilldex.validator import (
    check_skill_md,
    looks_like_secret,
    parse_frontmatter,
    validate_agent_md,
    validate_entry,
    validate_skill_md,
)

VALID_SKILL_ENTRY = {
    "id": "pdf",
    "type": "skill",
    "name": "PDF Toolkit",
    "description": "Work with PDFs.",
    "source": {"repo": "anthropics/skills", "path": "skills/pdf"},
}

VALID_MCP_ENTRY = {
    "id": "fetch",
    "type": "mcp",
    "name": "Fetch",
    "description": "Fetch web pages.",
    "mcp": {"type": "stdio", "command": "uvx", "args": ["mcp-server-fetch"]},
}


def test_valid_skill_entry():
    assert validate_entry(VALID_SKILL_ENTRY) == []


def test_valid_mcp_entry():
    assert validate_entry(VALID_MCP_ENTRY) == []


def test_missing_fields():
    errors = validate_entry({"id": "x"})
    assert any("type" in e for e in errors)
    assert any("name" in e for e in errors)
    assert any("description" in e for e in errors)


def test_bad_id_format():
    entry = {**VALID_SKILL_ENTRY, "id": "Bad_ID"}
    assert any("kebab-case" in e for e in validate_entry(entry))


def test_id_must_match_filename():
    errors = validate_entry(VALID_SKILL_ENTRY, filename="registry/skills/other.json")
    assert any("match filename" in e for e in errors)
    assert validate_entry(VALID_SKILL_ENTRY, filename="registry/skills/pdf.json") == []


def test_skill_requires_source_repo():
    entry = {**VALID_SKILL_ENTRY, "source": {"path": "skills/pdf"}}
    assert any("source.repo" in e for e in validate_entry(entry))


def test_mcp_http_requires_url():
    entry = {**VALID_MCP_ENTRY, "mcp": {"type": "http"}}
    assert any("mcp.url" in e for e in validate_entry(entry))


def test_mcp_entry_rejects_hardcoded_secret():
    entry = {
        **VALID_MCP_ENTRY,
        "mcp": {
            "type": "stdio",
            "command": "uvx",
            "env": {"API_KEY": "sk-abcdefghijklmnop1234"},
        },
    }
    assert any("secret" in e for e in validate_entry(entry))


def test_looks_like_secret():
    assert looks_like_secret("ghp_" + "a" * 30)
    assert looks_like_secret("sk-" + "a" * 24)
    assert not looks_like_secret("${GITHUB_TOKEN}")
    # "task-breakdown" contains "sk-" mid-word — must not be flagged
    assert not looks_like_secret("planning-and-task-breakdown-methodology")


def test_parse_frontmatter_roundtrip():
    fm, body = parse_frontmatter("---\nname: x\n---\nbody here")
    assert fm == {"name": "x"}
    assert body == "body here"


def test_parse_frontmatter_absent():
    fm, body = parse_frontmatter("just a doc")
    assert fm is None
    assert body == "just a doc"


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_valid_skill_md(tmp_path):
    p = _write(
        tmp_path,
        "SKILL.md",
        "---\nname: my-skill\ndescription: Does a thing when asked.\n---\n# Usage\nDo it.\n",
    )
    assert validate_skill_md(p) == []


def test_skill_md_missing_frontmatter(tmp_path):
    p = _write(tmp_path, "SKILL.md", "# No frontmatter here\n")
    assert any("frontmatter" in e for e in validate_skill_md(p))


def test_skill_md_bad_name(tmp_path):
    p = _write(
        tmp_path,
        "SKILL.md",
        "---\nname: My Skill\ndescription: ok\n---\nbody\n",
    )
    assert any("kebab-case" in e for e in validate_skill_md(p))


def test_skill_md_long_body_is_warning_not_error(tmp_path):
    body = "word " * 5001
    p = _write(
        tmp_path,
        "SKILL.md",
        f"---\nname: my-skill\ndescription: ok\n---\n{body}",
    )
    errors, warnings = check_skill_md(p)
    assert errors == []
    assert any("5000 words" in w for w in warnings)


def test_skill_md_empty_body(tmp_path):
    p = _write(tmp_path, "SKILL.md", "---\nname: my-skill\ndescription: ok\n---\n")
    assert any("body is empty" in e for e in validate_skill_md(p))


def test_agent_md_valid(tmp_path):
    p = _write(
        tmp_path,
        "reviewer.md",
        "---\nname: reviewer\ndescription: Reviews code.\n---\nYou are a code reviewer.\n",
    )
    assert validate_agent_md(p) == []


def test_agent_md_missing_description(tmp_path):
    p = _write(tmp_path, "reviewer.md", "---\nname: reviewer\n---\nprompt\n")
    assert any("description" in e for e in validate_agent_md(p))
