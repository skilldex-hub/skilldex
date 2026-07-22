import io
import json
import tarfile

from skilldex.installer import extract_subdir, install_mcp


def _make_tarball(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def test_extract_subdir_strips_prefix_and_filters(tmp_path):
    tarball = _make_tarball(
        {
            "repo-HEAD/skills/pdf/SKILL.md": "pdf skill",
            "repo-HEAD/skills/pdf/scripts/fill.py": "code",
            "repo-HEAD/skills/other/SKILL.md": "other",
            "repo-HEAD/README.md": "readme",
        }
    )
    written = extract_subdir(tarball, "skills/pdf", tmp_path / "pdf")
    assert written == 2
    assert (tmp_path / "pdf" / "SKILL.md").read_text() == "pdf skill"
    assert (tmp_path / "pdf" / "scripts" / "fill.py").exists()
    assert not (tmp_path / "pdf" / "README.md").exists()


def test_extract_subdir_whole_repo(tmp_path):
    tarball = _make_tarball({"repo-HEAD/README.md": "hi", "repo-HEAD/src/a.py": "a"})
    assert extract_subdir(tarball, ".", tmp_path / "out") == 2


def test_extract_subdir_blocks_path_traversal(tmp_path):
    tarball = _make_tarball({"repo-HEAD/skills/pdf/../../../evil.txt": "evil"})
    dest = tmp_path / "safe"
    extract_subdir(tarball, "skills/pdf", dest)
    assert not (tmp_path / "evil.txt").exists()
    assert not (tmp_path.parent / "evil.txt").exists()

MCP_ENTRY = {
    "id": "fetch",
    "type": "mcp",
    "name": "Fetch",
    "description": "Fetch web pages.",
    "mcp": {"type": "stdio", "command": "uvx", "args": ["mcp-server-fetch"]},
}


def test_install_mcp_creates_config(tmp_path):
    config_path = tmp_path / ".mcp.json"
    install_mcp(MCP_ENTRY, config_path)
    config = json.loads(config_path.read_text())
    assert config["mcpServers"]["fetch"]["command"] == "uvx"


def test_install_mcp_preserves_existing_servers_and_other_keys(tmp_path):
    """Global installs write into ~/.claude.json, which holds unrelated Claude
    Code state — merging must never drop it."""
    config_path = tmp_path / ".claude.json"
    config_path.write_text(
        json.dumps(
            {
                "someClaudeCodeState": {"theme": "dark"},
                "mcpServers": {"existing": {"command": "npx", "args": ["existing-server"]}},
            }
        )
    )
    install_mcp(MCP_ENTRY, config_path)
    config = json.loads(config_path.read_text())
    assert config["someClaudeCodeState"] == {"theme": "dark"}
    assert config["mcpServers"]["existing"]["args"] == ["existing-server"]
    assert config["mcpServers"]["fetch"]["command"] == "uvx"


def test_install_mcp_overwrites_same_id(tmp_path):
    config_path = tmp_path / ".mcp.json"
    install_mcp(MCP_ENTRY, config_path)
    updated = {**MCP_ENTRY, "mcp": {"type": "stdio", "command": "npx", "args": ["new"]}}
    install_mcp(updated, config_path)
    config = json.loads(config_path.read_text())
    assert config["mcpServers"]["fetch"]["command"] == "npx"
