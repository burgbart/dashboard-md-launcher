from __future__ import annotations

import json
import sys
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .config import CONFIG_PATH, DashboardEntry, find_dashboard, load_config
from .registry import find_instance, prune_registry, wait_for_instance
from .viewer import resolve_dashboard_path, spawn_viewer

HUB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboards</title>
  <style>
    :root {
      --bg: #0d1117;
      --surface: #161b22;
      --surface-2: #1c2128;
      --border: #30363d;
      --text: #c9d1d9;
      --heading: #e6edf3;
      --accent: #58a6ff;
      --muted: #8b949e;
      --ok-text: #3fb950;
      --idle: #6e7681;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      line-height: 1.5;
    }
    .wrap { max-width: 960px; margin: 0 auto; padding: 32px 20px 48px; }
    h1 { color: var(--heading); font-size: 1.75rem; margin: 0 0 8px; }
    .subtitle { color: var(--muted); margin-bottom: 24px; }
    .toolbar { display: flex; gap: 12px; margin-bottom: 20px; align-items: center; }
    input[type="search"] {
      flex: 1;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--heading);
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 14px;
    }
    input[type="search"]:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15);
    }
    .meta { color: var(--muted); font-size: 13px; white-space: nowrap; }
    .list { display: grid; gap: 12px; }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      display: grid;
      gap: 8px;
    }
    .card-head { display: flex; justify-content: space-between; gap: 12px; align-items: start; }
    .card h2 { margin: 0; color: var(--heading); font-size: 1rem; }
    .badge {
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      border-radius: 999px;
      padding: 4px 8px;
      white-space: nowrap;
    }
    .badge.running { background: rgba(35, 134, 54, 0.2); color: var(--ok-text); }
    .badge.stopped { background: rgba(110, 118, 129, 0.2); color: var(--idle); }
    .path {
      color: var(--muted);
      font-size: 12px;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      word-break: break-all;
    }
    .desc { color: var(--text); font-size: 13px; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; }
    button, .link-btn {
      appearance: none;
      border: 1px solid var(--border);
      background: var(--surface-2);
      color: var(--heading);
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 13px;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
    }
    button.primary, .link-btn.primary {
      background: var(--accent);
      border-color: var(--accent);
      color: #0d1117;
      font-weight: 600;
    }
    button:disabled { opacity: 0.6; cursor: wait; }
    .empty {
      border: 1px dashed var(--border);
      border-radius: 10px;
      padding: 28px;
      color: var(--muted);
      text-align: center;
    }
    .empty code { color: var(--heading); }
    .toast {
      position: fixed;
      right: 20px;
      bottom: 20px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--heading);
      padding: 10px 14px;
      border-radius: 8px;
      opacity: 0;
      transform: translateY(8px);
      transition: all 0.2s ease;
      pointer-events: none;
    }
    .toast.show { opacity: 1; transform: translateY(0); }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Dashboards</h1>
    <p class="subtitle">Configured dashboards on this laptop. Search, open, or start on demand.</p>
    <div class="toolbar">
      <input id="search" type="search" placeholder="Search by name, id, path, or description..." autofocus>
      <span id="count" class="meta"></span>
    </div>
    <div id="list" class="list"></div>
  </div>
  <div id="toast" class="toast"></div>
  <script>
    const listEl = document.getElementById('list');
    const searchEl = document.getElementById('search');
    const countEl = document.getElementById('count');
    const toastEl = document.getElementById('toast');
    let dashboards = [];

    function showToast(message) {
      toastEl.textContent = message;
      toastEl.classList.add('show');
      clearTimeout(showToast._timer);
      showToast._timer = setTimeout(() => toastEl.classList.remove('show'), 2200);
    }

    function matches(entry, query) {
      if (!query) return true;
      const haystack = [
        entry.id, entry.name, entry.path, entry.description || '',
        entry.running ? 'running' : 'stopped',
      ].join(' ').toLowerCase();
      return haystack.includes(query);
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;');
    }

    function render() {
      const query = searchEl.value.trim().toLowerCase();
      const visible = dashboards.filter((entry) => matches(entry, query));
      countEl.textContent = `${visible.length} of ${dashboards.length}`;

      if (!dashboards.length) {
        listEl.innerHTML = '<div class="empty">No dashboards configured yet.<br>Add one with <code>dashboard-hub add "My Project" ~/path/to/project</code></div>';
        return;
      }
      if (!visible.length) {
        listEl.innerHTML = '<div class="empty">No dashboards match your search.</div>';
        return;
      }

      listEl.innerHTML = visible.map((entry) => {
        const status = entry.running ? 'running' : 'stopped';
        const statusLabel = entry.running ? 'Running' : 'Stopped';
        const openLabel = entry.running ? 'Open' : 'Start & Open';
        const openUrl = entry.url || '#';
        return `
          <article class="card" data-id="${entry.id}">
            <div class="card-head">
              <h2>${escapeHtml(entry.name)}</h2>
              <span class="badge ${status}">${statusLabel}</span>
            </div>
            <div class="path">${escapeHtml(entry.path)}</div>
            ${entry.description ? `<div class="desc">${escapeHtml(entry.description)}</div>` : ''}
            <div class="actions">
              <button class="primary" data-action="open" data-id="${entry.id}">${openLabel}</button>
              ${entry.running ? `<a class="link-btn" href="${escapeHtml(openUrl)}" target="_blank" rel="noopener">Open in new tab</a>` : ''}
            </div>
          </article>
        `;
      }).join('');
    }

    async function refresh() {
      const res = await fetch('/api/dashboards');
      dashboards = await res.json();
      render();
    }

    async function openDashboard(id, button) {
      button.disabled = true;
      try {
        const res = await fetch(`/api/dashboards/${encodeURIComponent(id)}/open`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to open dashboard');
        showToast(data.started ? 'Started dashboard' : 'Opened dashboard');
        window.open(data.url, '_blank', 'noopener');
        await refresh();
      } catch (error) {
        showToast(error.message);
      } finally {
        button.disabled = false;
      }
    }

    listEl.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.dataset.action === 'open') {
        openDashboard(target.dataset.id, target);
      }
    });

    searchEl.addEventListener('input', render);
    refresh();
    setInterval(refresh, 3000);
  </script>
</body>
</html>
"""


@dataclass
class HubContext:
    tool_root: Path


class HubHandler(BaseHTTPRequestHandler):
    context: HubContext

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/dashboards", "/dashboards/"):
            self._serve_html()
            return
        if parsed.path == "/api/dashboards":
            self._serve_dashboards()
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        prefix = "/api/dashboards/"
        suffix = "/open"
        if parsed.path.startswith(prefix) and parsed.path.endswith(suffix):
            dashboard_id = parsed.path[len(prefix) : -len(suffix)]
            self._open_dashboard(dashboard_id)
            return
        self.send_error(404)

    def _serve_html(self):
        self._send_bytes(200, "text/html; charset=utf-8", HUB_HTML.encode("utf-8"))

    def _serve_dashboards(self):
        config = load_config()
        payload = [self._serialize_dashboard(entry, config.hub.host) for entry in config.dashboards]
        self._send_bytes(200, "application/json", json.dumps(payload).encode("utf-8"))

    def _serialize_dashboard(self, entry: DashboardEntry, host: str) -> dict:
        instance = find_instance(entry.id)
        return {
            "id": entry.id,
            "name": entry.name,
            "path": str(entry.path),
            "description": entry.description,
            "running": instance is not None,
            "url": instance.url if instance else None,
            "port": instance.port if instance else None,
        }

    def _open_dashboard(self, dashboard_id: str):
        config = load_config()
        entry = find_dashboard(config, dashboard_id)
        if not entry:
            self._send_json(404, {"error": f"Unknown dashboard id: {dashboard_id}"})
            return
        try:
            resolve_dashboard_path(entry.path)
        except FileNotFoundError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        instance = find_instance(entry.id)
        if instance:
            self._send_json(200, {"url": instance.url, "started": False})
            return

        spawn_viewer(entry)
        instance = wait_for_instance(entry.id)
        if not instance:
            self._send_json(500, {"error": "Dashboard failed to start"})
            return
        self._send_json(200, {"url": instance.url, "started": True})

    def _send_json(self, status: int, payload: dict):
        self._send_bytes(status, "application/json", json.dumps(payload).encode("utf-8"))

    def _send_bytes(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)


def run_server(*, open_browser: bool = True) -> None:
    config = load_config()
    host = config.hub.host
    port = config.hub.port
    tool_root = Path(__file__).resolve().parent.parent

    HubHandler.context = HubContext(tool_root=tool_root)
    prune_registry(host)

    try:
        server = ThreadingHTTPServer((host, port), HubHandler)
    except OSError as exc:
        print(f"Error: could not bind {host}:{port} ({exc})", file=sys.stderr)
        raise SystemExit(1) from exc

    url = f"http://{host}:{port}/dashboards/"
    print(f"Dashboard hub running at {url}")
    print(f"Config: {CONFIG_PATH}")
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
