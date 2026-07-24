from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from . import __version__
from .backlog_browser import (
    launch_backlog_browser,
    read_backlog_project_name,
    resolve_backlog_project,
    run_backlog_browser,
)
from .config import CONFIG_PATH, DashboardEntry, find_dashboard, load_config, save_config, slugify
from .registry import find_instance, prune_registry
from .server import run_server


def cmd_server(args: argparse.Namespace) -> None:
    run_server(open_browser=not args.no_open)


def cmd_browser(args: argparse.Namespace) -> None:
    config = load_config()
    entry = find_dashboard(config, args.id)
    if not entry:
        print(f"Error: unknown project id '{args.id}'", file=sys.stderr)
        raise SystemExit(1)
    run_backlog_browser(entry, open_browser=not args.no_open, register=False)


def cmd_dash(args: argparse.Namespace) -> None:
    config = load_config()
    project_path = Path(args.path).resolve()
    resolve_backlog_project(project_path)

    entry = find_dashboard(config, args.id) if args.id else None
    if entry is None:
        entry = DashboardEntry(
            id=args.id or slugify(project_path.name),
            name=args.name or read_backlog_project_name(project_path) or project_path.name,
            path=project_path,
            description=args.description or "",
        )
        if args.register:
            existing = find_dashboard(config, entry.id)
            if existing is None:
                config.dashboards.append(entry)
                save_config(config)
            else:
                entry = existing

    run_backlog_browser(entry, open_browser=not args.no_open, register=False)


def cmd_add(args: argparse.Namespace) -> None:
    config = load_config()
    project_path = Path(args.path).resolve()
    resolve_backlog_project(project_path)

    dashboard_id = args.id or slugify(args.name)
    if find_dashboard(config, dashboard_id):
        print(f"Error: project id '{dashboard_id}' already exists", file=sys.stderr)
        raise SystemExit(1)

    entry = DashboardEntry(
        id=dashboard_id,
        name=args.name,
        path=project_path,
        description=args.description or "",
    )
    config.dashboards.append(entry)
    save_config(config)
    print(f"Added '{entry.name}' as '{entry.id}'")
    print(f"Config: {CONFIG_PATH}")


def cmd_remove(args: argparse.Namespace) -> None:
    config = load_config()
    before = len(config.dashboards)
    config.dashboards = [item for item in config.dashboards if item.id != args.id]
    if len(config.dashboards) == before:
        print(f"Error: project id '{args.id}' not found", file=sys.stderr)
        raise SystemExit(1)
    save_config(config)
    print(f"Removed '{args.id}'")


def cmd_list(args: argparse.Namespace) -> None:
    config = load_config()
    prune_registry(config.hub.host)
    if not config.dashboards:
        print("No projects configured.")
        print('Add one: dashboard-hub add "My Project" ~/path/to/project')
        return

    for entry in config.dashboards:
        instance = find_instance(entry.id)
        status = "running" if instance else "stopped"
        url = f" ({instance.url})" if instance else ""
        print(f"- {entry.id}: {entry.name} [{status}]{url}")
        print(f"  {entry.path}")
        if entry.description:
            print(f"  {entry.description}")


def cmd_open(args: argparse.Namespace) -> None:
    config = load_config()
    entry = find_dashboard(config, args.id)
    if not entry:
        print(f"Error: project id '{args.id}' not found", file=sys.stderr)
        raise SystemExit(1)
    resolve_backlog_project(entry.path)

    instance = find_instance(entry.id)
    if instance:
        url = instance.url
    else:
        try:
            instance = launch_backlog_browser(entry)
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        url = instance.url

    if not args.no_open:
        if sys.platform == "darwin":
            subprocess.run(["open", url], check=False)
        else:
            import webbrowser

            webbrowser.open(url)
    print(url)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dashboard-hub",
        description="Local hub for browsing, searching, and launching Backlog.md browser UIs.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    server = subparsers.add_parser("server", help="Run the project hub UI")
    server.add_argument("--no-open", action="store_true", help="Do not open a browser tab")
    server.set_defaults(func=cmd_server)

    browser = subparsers.add_parser("browser", help="Run Backlog.md browser for a configured project")
    browser.add_argument("--id", required=True, help="Project id from config")
    browser.add_argument("--no-open", action="store_true", help="Do not open a browser tab")
    browser.set_defaults(func=cmd_browser)

    dash = subparsers.add_parser("dash", help="Run Backlog.md browser in the current or given project")
    dash.add_argument("path", nargs="?", default=".", help="Project path (default: current directory)")
    dash.add_argument("--id", help="Project id (defaults to folder name slug)")
    dash.add_argument("--name", help="Display name (defaults to backlog project name)")
    dash.add_argument("--description", default="", help="Optional description")
    dash.add_argument("--register", action="store_true", help="Add to config if not present")
    dash.add_argument("--no-open", action="store_true", help="Do not open a browser tab")
    dash.set_defaults(func=cmd_dash)

    add = subparsers.add_parser("add", help="Register a Backlog.md project in config")
    add.add_argument("name", help="Display name")
    add.add_argument("path", help="Project path containing backlog/config.yml")
    add.add_argument("--id", help="Stable id (defaults to slug of name)")
    add.add_argument("--description", default="", help="Optional description")
    add.set_defaults(func=cmd_add)

    remove = subparsers.add_parser("remove", help="Remove a project from config")
    remove.add_argument("id", help="Project id")
    remove.set_defaults(func=cmd_remove)

    list_cmd = subparsers.add_parser("list", help="List configured projects")
    list_cmd.set_defaults(func=cmd_list)

    open_cmd = subparsers.add_parser("open", help="Open a backlog browser, starting it if needed")
    open_cmd.add_argument("id", help="Project id")
    open_cmd.add_argument("--no-open", action="store_true", help="Print URL only")
    open_cmd.set_defaults(func=cmd_open)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
