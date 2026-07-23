from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from .config import DashboardEntry, load_config
from .registry import (
    RunningInstance,
    find_free_port,
    register_instance,
    unregister_instance,
    utc_now,
)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {
      --bg: #0d1117;
      --surface: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --heading: #e6edf3;
      --accent: #58a6ff;
      --code-bg: #1c2128;
      --muted: #8b949e;
      --ok: #3fb950;
      --warn: #f85149;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 14px;
      line-height: 1.6;
      min-height: 100%;
    }
    #status-bar {
      position: fixed;
      top: 0; left: 0; right: 0;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 6px 14px;
      font-size: 12px;
      color: var(--muted);
      z-index: 100;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }
    #status-bar .dot {
      display: inline-block;
      width: 7px; height: 7px;
      border-radius: 50%;
      background: var(--ok);
      margin-right: 6px;
      vertical-align: middle;
    }
    #status-bar .dot.stale { background: var(--warn); }
    #app {
      max-width: 900px;
      margin: 0 auto;
      padding: 52px 20px 40px;
    }
    #content h1, #content h2, #content h3,
    #content h4, #content h5, #content h6 {
      color: var(--heading);
      border-bottom: 1px solid var(--border);
      padding-bottom: 6px;
      margin: 20px 0 10px;
    }
    #content h1 { font-size: 1.5em; }
    #content h2 { font-size: 1.25em; }
    #content h3 { font-size: 1.1em; border-bottom: none; }
    #content p { margin: 8px 0; }
    #content ul, #content ol { margin: 6px 0 6px 20px; }
    #content li { margin: 2px 0; }
    #content code {
      background: var(--code-bg);
      padding: 1px 5px;
      border-radius: 4px;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.9em;
    }
    #content pre {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px;
      overflow-x: auto;
      margin: 10px 0;
    }
    #content pre code { background: none; padding: 0; }
    #content blockquote {
      border-left: 3px solid var(--border);
      padding-left: 12px;
      color: var(--muted);
      margin: 8px 0;
    }
    #content table {
      border-collapse: collapse;
      width: 100%;
      margin: 10px 0;
      font-size: 0.92em;
    }
    #content th, #content td {
      border: 1px solid var(--border);
      padding: 5px 10px;
      text-align: left;
    }
    #content th {
      background: var(--surface);
      color: var(--heading);
    }
    #content a { color: var(--accent); text-decoration: none; }
    #content a:hover { text-decoration: underline; }
    #content hr {
      border: none;
      border-top: 1px solid var(--border);
      margin: 16px 0;
    }
  </style>
</head>
<body>
  <div id="status-bar">
    <span><span id="dot" class="dot"></span><span id="status-text">Connecting...</span></span>
    <span id="last-updated"></span>
  </div>
  <div id="app"><div id="content">Loading...</div></div>
  <script>
    let lastMtime = null;
    const dot = document.getElementById('dot');
    const statusText = document.getElementById('status-text');
    const lastUpdated = document.getElementById('last-updated');
    const contentEl = document.getElementById('content');

    async function fetchMtime() {
      const res = await fetch('/api/mtime');
      const data = await res.json();
      return data.mtime;
    }

    async function fetchDashboard() {
      const res = await fetch('/api/dashboard');
      return await res.text();
    }

    async function render() {
      const md = await fetchDashboard();
      contentEl.innerHTML = marked.parse(md);
    }

    function setStatus(ok, text) {
      dot.className = 'dot' + (ok ? '' : ' stale');
      statusText.textContent = text;
    }

    async function poll() {
      try {
        const mtime = await fetchMtime();
        if (mtime !== lastMtime) {
          lastMtime = mtime;
          await render();
          const d = new Date();
          lastUpdated.textContent = 'Updated ' + d.toLocaleTimeString();
        }
        setStatus(true, 'Live');
      } catch (e) {
        setStatus(false, 'Connection error');
      }
    }

    poll();
    setInterval(poll, 1500);
  </script>
</body>
</html>
"""


class ViewerHandler(http.server.BaseHTTPRequestHandler):
    dashboard_path: Path
    dashboard_id: str
    dashboard_name: str
    project_path: Path
    port: int

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            self._serve_html()
        elif self.path == "/api/dashboard":
            self._serve_markdown()
        elif self.path == "/api/mtime":
            self._serve_mtime()
        else:
            self.send_error(404)

    def _serve_html(self):
        body = HTML_TEMPLATE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_markdown(self):
        try:
            text = self.dashboard_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.send_error(404, "dashboard.md not found")
            return
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_mtime(self):
        try:
            mtime = self.dashboard_path.stat().st_mtime
        except FileNotFoundError:
            self.send_error(404, "dashboard.md not found")
            return
        body = json.dumps({"mtime": mtime}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def resolve_dashboard_path(project_path: Path) -> Path:
    dashboard_path = project_path / "dashboard.md"
    if not dashboard_path.exists():
        raise FileNotFoundError(f"dashboard.md not found in {project_path}")
    return dashboard_path


def run_viewer(
    entry: DashboardEntry,
    *,
    port: int | None = None,
    open_browser: bool = False,
    register: bool = True,
) -> None:
    config = load_config()
    host = config.hub.host
    dashboard_path = resolve_dashboard_path(entry.path)
    chosen_port = port or find_free_port(*config.port_range, host=host)
    url = f"http://{host}:{chosen_port}"

    ViewerHandler.dashboard_path = dashboard_path
    ViewerHandler.dashboard_id = entry.id
    ViewerHandler.dashboard_name = entry.name
    ViewerHandler.project_path = entry.path
    ViewerHandler.port = chosen_port

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

    try:
        server = http.server.HTTPServer((host, chosen_port), ViewerHandler)
    except OSError as exc:
        print(f"Error: could not bind {host}:{chosen_port} ({exc})", file=sys.stderr)
        if register:
            unregister_instance(entry.id)
        raise SystemExit(1) from exc

    print(f"Dashboard viewer running at {url}")
    print(f"Serving: {dashboard_path}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        def _open():
            import time

            time.sleep(0.3)
            webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
        if register:
            unregister_instance(entry.id)


def spawn_viewer(entry: DashboardEntry) -> subprocess.Popen:
    tool_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{tool_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "dashboard_hub",
            "viewer",
            "--id",
            entry.id,
            "--no-open",
        ],
        cwd=str(entry.path),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
