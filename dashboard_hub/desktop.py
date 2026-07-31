from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from .config import load_config
from .registry import list_instances, terminate_instance, unregister_instance
from .server import create_server


def augment_path() -> None:
    """Add common CLI install locations to PATH.

    Apps launched from a GUI (Finder, Start Menu, desktop launcher) inherit a
    minimal PATH, so `backlog` (and `node`, which the backlog shim needs) may
    not be found even though they work fine in a terminal.
    """
    if sys.platform == "win32":
        candidates = [Path(os.environ.get("APPDATA", "")) / "npm"]
    else:
        candidates = [
            Path("/opt/homebrew/bin"),
            Path("/usr/local/bin"),
            Path.home() / ".local" / "bin",
        ]

    parts = os.environ.get("PATH", "").split(os.pathsep)
    for candidate in candidates:
        location = str(candidate)
        if candidate.is_dir() and location not in parts:
            parts.append(location)
    os.environ["PATH"] = os.pathsep.join(parts)


def stop_all_dashboards() -> None:
    """Terminate every dashboard tracked in the registry."""
    host = load_config().hub.host
    for instance in list_instances(host):
        terminate_instance(instance)
        unregister_instance(instance.id)


def run_desktop() -> None:
    """Run the hub inside a native webview window instead of a browser tab."""
    try:
        import webview
    except ImportError:
        print(
            "Error: pywebview is not installed. Install with: pip install pywebview",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    augment_path()
    server, url = create_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Dashboard hub running at {url}")
    print("Close the window to stop.")

    webview.create_window("Dashboard Hub", url, width=1280, height=800)
    try:
        webview.start()
    finally:
        server.shutdown()
        server.server_close()
        stop_all_dashboards()
