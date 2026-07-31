from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import __version__
from .backlog_browser import (
    choose_port,
    configured_backlog_port,
    launch_backlog_browser,
    read_backlog_project_name,
    resolve_backlog_project,
    run_backlog_browser,
)
from .config import CONFIG_PATH, DashboardEntry, find_dashboard, load_config, save_config, slugify
from .project_config import read_project_label
from .registry import (
    find_instance,
    instance_healthy,
    load_registry,
    process_cwd,
    process_tree_pids,
    prune_registry,
    terminate_process_tree,
)
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
    entry.port = choose_port(entry, host=config.hub.host)
    config.dashboards.append(entry)
    save_config(config)
    print(f"Added '{entry.name}' as '{entry.id}'")
    print(f"Assigned port: {entry.port}")
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
        label = read_project_label(entry.path)
        label_suffix = f" ({label})" if label else ""
        print(f"- {entry.id}: {entry.name}{label_suffix} [{status}]{url}")
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


def _win_backlog_browser_roots() -> list[tuple[int, Path | None]]:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | "
                "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        data = json.loads(result.stdout or "[]")
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []

    if isinstance(data, dict):
        data = [data]

    processes: dict[int, int] = {}
    matches: set[int] = set()
    for item in data:
        pid, parent, cmdline = item.get("ProcessId"), item.get("ParentProcessId"), item.get("CommandLine") or ""
        if pid is None or parent is None:
            continue
        pid, parent = int(pid), int(parent)
        processes[pid] = parent
        if "backlog" in cmdline and "browser" in cmdline:
            matches.add(pid)

    roots = [pid for pid in matches if processes.get(pid) not in processes]
    return [(pid, process_cwd(pid)) for pid in sorted(roots)]


def _backlog_browser_roots() -> list[tuple[int, Path | None]]:
    if sys.platform == "win32":
        return _win_backlog_browser_roots()

    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,command="],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    processes: dict[int, int] = {}
    for line in result.stdout.splitlines():
        fields = line.strip().split(maxsplit=2)
        if len(fields) != 3 or "backlog browser" not in fields[2]:
            continue
        try:
            processes[int(fields[0])] = int(fields[1])
        except ValueError:
            continue

    roots = [pid for pid, parent in processes.items() if parent not in processes]
    return [(pid, process_cwd(pid)) for pid in sorted(roots)]


def cmd_doctor(args: argparse.Namespace) -> None:
    config = load_config()
    configured_ports: dict[int, list[DashboardEntry]] = {}
    for entry in config.dashboards:
        configured_ports.setdefault(configured_backlog_port(entry.path), []).append(entry)

    collisions = {
        port: entries
        for port, entries in configured_ports.items()
        if len(entries) > 1
    }
    if collisions:
        print("Backlog default-port collisions:")
        for port, entries in sorted(collisions.items()):
            assignments = ", ".join(
                f"{entry.id} -> {entry.port or 'unassigned'}" for entry in entries
            )
            print(f"- {port}: {assignments}")
    else:
        print("Backlog default-port collisions: none")

    registry = load_registry()
    healthy = [
        instance for instance in registry if instance_healthy(instance, config.hub.host)
    ]
    stale = [instance for instance in registry if instance not in healthy]
    print(f"Registry: {len(healthy)} healthy, {len(stale)} stale")

    managed_pids: set[int] = set()
    for instance in healthy:
        managed_pids.update(process_tree_pids(instance.pid))
    project_paths = {entry.path.resolve() for entry in config.dashboards}
    orphans = [
        (pid, path)
        for pid, path in _backlog_browser_roots()
        if path in project_paths and pid not in managed_pids
    ]
    if orphans:
        print("Orphaned Backlog browsers:")
        for pid, path in orphans:
            print(f"- pid {pid}: {path}")
    else:
        print("Orphaned Backlog browsers: none")

    if args.clean:
        for pid, _ in orphans:
            terminate_process_tree(pid)
        prune_registry(config.hub.host)
        print(
            f"Removed {len(stale)} stale registry entries and "
            f"terminated {len(orphans)} orphaned process trees."
        )
    elif stale or orphans:
        print("Run `dashboard-hub doctor --clean` to remove stale processes.")


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

    doctor = subparsers.add_parser(
        "doctor",
        help="Check port collisions and orphaned Backlog browser processes",
    )
    doctor.add_argument(
        "--clean",
        action="store_true",
        help="Remove stale records and terminate orphaned browser processes",
    )
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
