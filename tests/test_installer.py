import json

from skilldex.installer import install_mcp

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
