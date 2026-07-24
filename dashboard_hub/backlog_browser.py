from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from .config import DashboardEntry, load_config
from .registry import (
    RunningInstance,
    find_free_port,
    port_open,
    register_instance,
    unregister_instance,
    utc_now,
)

BACKLOG_CONFIG_PATHS = (
    "backlog/config.yml",
    "backlog.config.yml",
    ".backlog/config.yml",
)


def backlog_config_path(project_path: Path) -> Path | None:
    for relative in BACKLOG_CONFIG_PATHS:
        candidate = project_path / relative
        if candidate.exists():
            return candidate
    return None


def has_backlog(project_path: Path) -> bool:
    return backlog_config_path(project_path) is not None


def resolve_backlog_project(project_path: Path) -> Path:
    project_path = project_path.resolve()
    if not has_backlog(project_path):
        raise FileNotFoundError(
            f"No Backlog.md project found in {project_path} "
            f"(expected one of: {', '.join(BACKLOG_CONFIG_PATHS)})"
        )
    return project_path


def read_backlog_port(project_path: Path) -> int | None:
    config_path = backlog_config_path(project_path)
    if config_path is None:
        return None
    match = re.search(r"^default_port:\s*(\d+)\s*$", config_path.read_text(encoding="utf-8"), re.M)
    if match:
        return int(match.group(1))
    return None


def read_backlog_project_name(project_path: Path) -> str | None:
    config_path = backlog_config_path(project_path)
    if config_path is None:
        return None
    match = re.search(r'^project_name:\s*"?([^"\n]+)"?\s*$', config_path.read_text(encoding="utf-8"), re.M)
    if match:
        return match.group(1).strip()
    return None


def backlog_binary() -> str:
    binary = shutil.which("backlog")
    if not binary:
        raise RuntimeError(
            "backlog CLI not found on PATH. Install with: npm i -g backlog.md"
        )
    return binary


def choose_port(entry: DashboardEntry, host: str = "127.0.0.1") -> int:
    config = load_config()
    preferred = read_backlog_port(entry.path)
    if preferred is not None:
        try:
            return find_free_port(preferred, preferred, host=host)
        except RuntimeError:
            pass
    return find_free_port(*config.port_range, host=host)


def browser_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/"


def spawn_backlog_browser(entry: DashboardEntry, port: int | None = None) -> subprocess.Popen:
    config = load_config()
    host = config.hub.host
    chosen_port = port or choose_port(entry, host=host)
    env = os.environ.copy()
    env["BACKLOG_CWD"] = str(entry.path)

    return subprocess.Popen(
        [
            backlog_binary(),
            "browser",
            "--port",
            str(chosen_port),
            "--no-open",
        ],
        cwd=str(entry.path),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def run_backlog_browser(
    entry: DashboardEntry,
    *,
    port: int | None = None,
    open_browser: bool = True,
    register: bool = False,
) -> None:
    config = load_config()
    host = config.hub.host
    resolve_backlog_project(entry.path)
    chosen_port = port or choose_port(entry, host=host)
    url = browser_url(host, chosen_port)

    if register:
        register_instance(
            RunningInstance(
                id=entry.id,
                name=entry.name,
                path=str(entry.path),
                url=url,
                port=chosen_port,
                pid=os.getpid(),
                started_at=utc_now(),
            )
        )

    print(f"Backlog browser running at {url}")
    print(f"Project: {entry.path}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        webbrowser.open(url)

    process = subprocess.Popen(
        [
            backlog_binary(),
            "browser",
            "--port",
            str(chosen_port),
            "--no-open",
        ],
        cwd=str(entry.path),
        env={**os.environ, "BACKLOG_CWD": str(entry.path)},
    )

    try:
        exit_code = process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("\nStopped.")
        if register:
            unregister_instance(entry.id)
        raise SystemExit(0) from None

    if register:
        unregister_instance(entry.id)
    raise SystemExit(exit_code)


def start_backlog_browser(entry: DashboardEntry, port: int | None = None) -> RunningInstance:
    """Spawn backlog browser detached and return instance metadata (not yet registered)."""
    config = load_config()
    host = config.hub.host
    resolve_backlog_project(entry.path)
    chosen_port = port or choose_port(entry, host=host)
    process = spawn_backlog_browser(entry, chosen_port)
    return RunningInstance(
        id=entry.id,
        name=entry.name,
        path=str(entry.path),
        url=browser_url(host, chosen_port),
        port=chosen_port,
        pid=process.pid,
        started_at=utc_now(),
    )


def launch_backlog_browser(entry: DashboardEntry) -> RunningInstance:
    import time

    from .registry import pid_alive, port_open, register_instance, unregister_instance

    config = load_config()
    host = config.hub.host
    instance = start_backlog_browser(entry)
    register_instance(instance)

    deadline = time.time() + 20
    while time.time() < deadline:
        if pid_alive(instance.pid) and port_open(host, instance.port):
            return instance
        if not pid_alive(instance.pid):
            break
        time.sleep(0.2)

    unregister_instance(entry.id)
    raise RuntimeError("Backlog browser failed to start")
