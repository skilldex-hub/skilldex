"""skilldex command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .audit import audit as run_audit
from .installer import agent_dest, install_mcp, install_source, skill_dest
from .registry import fetch_index, get_entry
from .registry import search as search_index
from .validator import check_skill_md, validate_agent_md, validate_entry

app = typer.Typer(
    help="Search, install, validate, and audit Claude Code skills, subagents, and MCP servers.",
    no_args_is_help=True,
)
console = Console()

TYPE_COLORS = {"skill": "green", "agent": "magenta", "mcp": "cyan"}


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"skilldex {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version."
    ),
) -> None:
    pass


def _load_index(refresh: bool = False) -> dict:
    try:
        return fetch_index(force=refresh)
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        console.print(f"[red]Could not fetch registry index:[/] {exc}")
        raise typer.Exit(2) from exc


@app.command()
def search(
    query: str = typer.Argument(..., help="Search terms, e.g. 'pdf' or 'github issues'."),
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter: skill, agent, or mcp."),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass the local index cache."),
) -> None:
    """Search the registry."""
    results = search_index(_load_index(refresh), query, type)
    if not results:
        console.print("[yellow]No matches.[/]")
        raise typer.Exit(1)
    table = Table(box=None, pad_edge=False)
    table.add_column("ID", style="bold")
    table.add_column("Type")
    table.add_column("Description", overflow="fold")
    for entry in results:
        etype = entry.get("type", "?")
        table.add_row(
            entry.get("id", "?"),
            f"[{TYPE_COLORS.get(etype, 'white')}]{etype}[/]",
            entry.get("description", ""),
        )
    console.print(table)


@app.command()
def show(entry_id: str = typer.Argument(..., help="Registry entry id.")) -> None:
    """Show the full registry entry."""
    entry = get_entry(_load_index(), entry_id)
    if entry is None:
        console.print(f"[red]No entry with id {entry_id!r}.[/] Try: skilldex search {entry_id}")
        raise typer.Exit(1)
    console.print_json(json.dumps(entry))


@app.command()
def install(
    entry_id: str = typer.Argument(..., help="Registry entry id."),
    project: bool = typer.Option(
        False, "--project", "-p", help="Install into ./.claude instead of ~/.claude."
    ),
) -> None:
    """Install a skill, subagent, or MCP server."""
    entry = get_entry(_load_index(), entry_id)
    if entry is None:
        console.print(f"[red]No entry with id {entry_id!r}.[/] Try: skilldex search {entry_id}")
        raise typer.Exit(1)

    etype = entry.get("type")
    if etype == "skill":
        dest = install_source(entry, skill_dest(project))
        console.print(f"[green]Installed skill[/] {entry_id} → {dest}")
    elif etype == "agent":
        dest = install_source(entry, agent_dest(project))
        console.print(f"[green]Installed agent[/] {entry_id} → {dest}")
    elif etype == "mcp":
        config_path = install_mcp(entry)
        console.print(f"[green]Added MCP server[/] {entry_id} → {config_path}")
        env = entry.get("mcp", {}).get("env") or {}
        placeholders = [k for k, v in env.items() if isinstance(v, str) and v.startswith("${")]
        if placeholders:
            console.print(
                f"[yellow]Set these environment variables:[/] {', '.join(placeholders)}"
            )
    else:
        console.print(f"[red]Unknown entry type {etype!r}.[/]")
        raise typer.Exit(2)


@app.command()
def validate(
    path: Path = typer.Argument(..., exists=True, help="SKILL.md, agent .md, entry .json, or a skill directory."),
) -> None:
    """Validate a SKILL.md, subagent file, or registry entry."""
    target = path / "SKILL.md" if path.is_dir() and (path / "SKILL.md").exists() else path
    warnings: list[str] = []
    if target.suffix == ".json":
        try:
            entry = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            console.print(f"[red]{target}: invalid JSON:[/] {exc}")
            raise typer.Exit(1) from exc
        errors = validate_entry(entry, filename=str(target))
    elif target.name == "SKILL.md":
        errors, warnings = check_skill_md(target)
    elif target.suffix == ".md":
        errors = validate_agent_md(target)
    else:
        console.print(f"[red]Don't know how to validate {target}[/] (expected .md or .json)")
        raise typer.Exit(2)

    for warning in warnings:
        console.print(f"[yellow]![/] {target}: {warning}")
    if errors:
        for error in errors:
            console.print(f"[red]✗[/] {target}: {error}")
        raise typer.Exit(1)
    console.print(f"[green]✓[/] {target} is valid")


@app.command()
def audit() -> None:
    """Audit local Claude Code config (skills, agents, .mcp.json) for problems."""
    findings = run_audit()
    if not findings:
        console.print("[green]✓ No problems found.[/]")
        return
    for location, problem in findings:
        console.print(f"[red]✗[/] {location}: {problem}")
    raise typer.Exit(1)


@app.command("list")
def list_installed() -> None:
    """List locally installed skills, agents, and project MCP servers."""
    table = Table(box=None, pad_edge=False)
    table.add_column("Type")
    table.add_column("Name", style="bold")
    table.add_column("Location")
    rows = 0
    for scope, base in (("user", Path.home()), ("project", Path.cwd())):
        skills = base / ".claude" / "skills"
        if skills.is_dir():
            for skill in sorted(p for p in skills.iterdir() if (p / "SKILL.md").exists()):
                table.add_row("[green]skill[/]", skill.name, f"{scope}: {skill}")
                rows += 1
        agents = base / ".claude" / "agents"
        if agents.is_dir():
            for agent in sorted(agents.rglob("*.md")):
                table.add_row("[magenta]agent[/]", agent.stem, f"{scope}: {agent}")
                rows += 1
    mcp_file = Path.cwd() / ".mcp.json"
    if mcp_file.exists():
        try:
            config = json.loads(mcp_file.read_text(encoding="utf-8"))
            for name in config.get("mcpServers") or {}:
                table.add_row("[cyan]mcp[/]", name, f"project: {mcp_file}")
                rows += 1
        except json.JSONDecodeError:
            console.print(f"[yellow]Warning: {mcp_file} is not valid JSON.[/]")
    if rows == 0:
        console.print("[yellow]Nothing installed yet.[/] Try: skilldex search <topic>")
        return
    console.print(table)
