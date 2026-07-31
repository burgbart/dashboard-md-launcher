from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

WINDOWS = sys.platform == "win32"

if WINDOWS:
    # CREATE_NO_WINDOW suppresses a console for our immediate child (the
    # backlog.cmd shim / node.exe), but node.exe re-spawns its own child
    # process (a compiled backlog.exe) without any creation flags of its
    # own. Since node.exe has no console (because of our flag), Windows
    # auto-allocates a fresh one for that grandchild per default CreateProcess
    # behavior. We can't pass flags into a spawn we don't control, so
    # _suppress_windows_console polls for and hides that window afterward.
    _DETACH_KWARGS = {
        "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    }
else:
    _DETACH_KWARGS = {"start_new_session": True}


def _suppress_windows_console(root_pid: int, attempts: int = 50, interval: float = 0.1) -> None:
    """Hide any console window opened by a descendant of root_pid (Windows only)."""
    import ctypes
    from ctypes import wintypes

    from .registry import process_tree_pids

    user32 = ctypes.windll.user32
    SW_HIDE = 0
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    for _ in range(attempts):
        pids = process_tree_pids(root_pid)
        hidden = False

        def _callback(hwnd, _lparam, _pids=pids):
            nonlocal hidden
            owner_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
            if owner_pid.value in _pids and user32.IsWindowVisible(hwnd):
                user32.ShowWindow(hwnd, SW_HIDE)
                hidden = True
            return True

        user32.EnumWindows(WNDENUMPROC(_callback), 0)
        if hidden:
            return
        time.sleep(interval)

from .config import DashboardEntry, load_config, save_config
from .registry import (
    RunningInstance,
    find_free_port,
    pid_alive,
    port_open,
    process_owns_port,
    register_instance,
    terminate_process_tree,
    unregister_instance,
    utc_now,
)

BACKLOG_CONFIG_PATHS = (
    "backlog/config.yml",
    "backlog.config.yml",
    ".backlog/config.yml",
)
DEFAULT_BACKLOG_PORT = 6420
_launch_lock = threading.Lock()


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


def configured_backlog_port(project_path: Path) -> int:
    return read_backlog_port(project_path) or DEFAULT_BACKLOG_PORT


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


def _reserved_ports(entry: DashboardEntry) -> set[int]:
    config = load_config()
    reserved = {
        item.port
        for item in config.dashboards
        if item.id != entry.id and item.port is not None
    }

    preferred = configured_backlog_port(entry.path)
    for item in config.dashboards:
        if item.id == entry.id:
            break
        if item.port is None and configured_backlog_port(item.path) == preferred:
            reserved.add(preferred)
            break
    return reserved


def choose_port(
    entry: DashboardEntry,
    host: str = "127.0.0.1",
    *,
    excluded: set[int] | None = None,
) -> int:
    config = load_config()
    unavailable = _reserved_ports(entry) | (excluded or set())
    candidates = [entry.port, configured_backlog_port(entry.path)]
    for candidate in candidates:
        if candidate is None or candidate in unavailable:
            continue
        try:
            return find_free_port(candidate, candidate, host=host)
        except RuntimeError:
            pass
    for candidate in range(config.port_range[0], config.port_range[1] + 1):
        if candidate in unavailable:
            continue
        try:
            return find_free_port(candidate, candidate, host=host)
        except RuntimeError:
            continue
    raise RuntimeError(
        f"No free port available in range {config.port_range[0]}-{config.port_range[1]}"
    )


def persist_entry_port(entry: DashboardEntry, port: int) -> None:
    config = load_config()
    for configured_entry in config.dashboards:
        if configured_entry.id == entry.id:
            configured_entry.port = port
            entry.port = port
            save_config(config)
            return


def browser_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/"


def spawn_backlog_browser(entry: DashboardEntry, port: int | None = None) -> subprocess.Popen:
    config = load_config()
    host = config.hub.host
    chosen_port = port or choose_port(entry, host=host)
    env = os.environ.copy()
    env["BACKLOG_CWD"] = str(entry.path)

    process = subprocess.Popen(
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
        **_DETACH_KWARGS,
    )
    if WINDOWS:
        threading.Thread(
            target=_suppress_windows_console, args=(process.pid,), daemon=True
        ).start()
    return process


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
        terminate_process_tree(process.pid)
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
    config = load_config()
    host = config.hub.host
    resolve_backlog_project(entry.path)
    attempted: set[int] = set()
    errors: list[str] = []

    with _launch_lock:
        for _ in range(3):
            chosen_port = choose_port(entry, host=host, excluded=attempted)
            attempted.add(chosen_port)
            process = spawn_backlog_browser(entry, chosen_port)
            deadline = time.time() + 20

            while time.time() < deadline:
                if not pid_alive(process.pid):
                    errors.append(f"process exited on port {chosen_port}")
                    break
                if port_open(host, chosen_port):
                    if process_owns_port(process.pid, chosen_port, entry.path):
                        instance = RunningInstance(
                            id=entry.id,
                            name=entry.name,
                            path=str(entry.path),
                            url=browser_url(host, chosen_port),
                            port=chosen_port,
                            pid=process.pid,
                            started_at=utc_now(),
                        )
                        persist_entry_port(entry, chosen_port)
                        register_instance(instance, host=host)
                        return instance
                    errors.append(f"port {chosen_port} is owned by another process")
                    break
                time.sleep(0.2)
            else:
                errors.append(f"timed out waiting for port {chosen_port}")

            terminate_process_tree(process.pid)

    unregister_instance(entry.id)
    detail = "; ".join(errors)
    raise RuntimeError(f"Backlog browser failed to start ({detail})")
