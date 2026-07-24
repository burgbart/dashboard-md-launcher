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
from .registry import find_instance, prune_registry
from .backlog_browser import launch_backlog_browser, resolve_backlog_project

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
      --ok: #3fb950;
      --idle: #6e7681;
      --sidebar-width: 280px;
      --sidebar-collapsed: 56px;
      --header-height: 52px;
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      height: 100%;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }
    button, input {
      font: inherit;
    }
    .shell {
      display: grid;
      grid-template-columns: var(--sidebar-width) 1fr;
      height: 100vh;
      transition: grid-template-columns 0.2s ease;
    }
    .shell.collapsed {
      grid-template-columns: var(--sidebar-collapsed) 1fr;
    }
    .sidebar {
      background: var(--surface);
      border-right: 1px solid var(--border);
      display: grid;
      grid-template-rows: auto auto 1fr auto;
      min-height: 0;
      overflow: hidden;
    }
    .sidebar-head {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px;
      border-bottom: 1px solid var(--border);
      min-height: var(--header-height);
    }
    .icon-btn {
      appearance: none;
      border: 1px solid var(--border);
      background: var(--surface-2);
      color: var(--heading);
      width: 32px;
      height: 32px;
      border-radius: 8px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: 0 0 auto;
    }
    .icon-btn:hover { border-color: var(--accent); }
    .brand {
      color: var(--heading);
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
    }
    .shell.collapsed .brand,
    .shell.collapsed .sidebar-search,
    .shell.collapsed .sidebar-foot,
    .shell.collapsed .nav-meta,
    .shell.collapsed .nav-name {
      display: none;
    }
    .sidebar-search {
      padding: 12px;
      border-bottom: 1px solid var(--border);
    }
    .sidebar-search input {
      width: 100%;
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--heading);
      border-radius: 8px;
      padding: 9px 10px;
      font-size: 13px;
    }
    .sidebar-search input:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15);
    }
    .nav {
      overflow: auto;
      padding: 8px;
      display: grid;
      gap: 4px;
      align-content: start;
    }
    .nav-item {
      appearance: none;
      border: 1px solid transparent;
      background: transparent;
      color: var(--text);
      border-radius: 8px;
      padding: 10px 12px;
      text-align: left;
      cursor: pointer;
      display: grid;
      grid-template-columns: 10px 1fr;
      gap: 10px;
      align-items: start;
      width: 100%;
    }
    .nav-item:hover {
      background: var(--surface-2);
      border-color: var(--border);
    }
    .nav-item.active {
      background: rgba(88, 166, 255, 0.12);
      border-color: rgba(88, 166, 255, 0.35);
    }
    .nav-item.loading {
      opacity: 0.7;
      cursor: wait;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-top: 5px;
      background: var(--idle);
      flex: 0 0 auto;
    }
    .status-dot.running { background: var(--ok); }
    .nav-copy { min-width: 0; }
    .nav-name {
      color: var(--heading);
      font-size: 13px;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .nav-meta {
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-top: 2px;
    }
    .shell.collapsed .nav-item {
      grid-template-columns: 1fr;
      justify-items: center;
      padding: 10px 8px;
    }
    .shell.collapsed .status-dot {
      margin-top: 0;
    }
    .sidebar-foot {
      border-top: 1px solid var(--border);
      padding: 10px 12px;
      color: var(--muted);
      font-size: 12px;
    }
    .main {
      display: grid;
      grid-template-rows: auto 1fr;
      min-width: 0;
      min-height: 0;
      background: var(--bg);
    }
    .main-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 10px 16px;
      border-bottom: 1px solid var(--border);
      min-height: var(--header-height);
      background: var(--surface);
    }
    .main-head.hidden { display: none; }
    .main-title h1 {
      margin: 0;
      color: var(--heading);
      font-size: 15px;
      font-weight: 600;
    }
    .main-title .path {
      color: var(--muted);
      font-size: 12px;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 60vw;
    }
    .main-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .btn {
      appearance: none;
      border: 1px solid var(--border);
      background: var(--surface-2);
      color: var(--heading);
      border-radius: 8px;
      padding: 7px 11px;
      font-size: 12px;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
    }
    .btn:hover { border-color: var(--accent); }
    .pane {
      position: relative;
      min-height: 0;
    }
    .empty-state,
    .loading-state {
      height: 100%;
      display: grid;
      place-content: center;
      text-align: center;
      color: var(--muted);
      padding: 24px;
      gap: 8px;
    }
    .empty-state code,
    .loading-state strong {
      color: var(--heading);
    }
    .hidden { display: none !important; }
    .frame {
      width: 100%;
      height: 100%;
      border: 0;
      background: var(--bg);
    }
    .spinner {
      width: 28px;
      height: 28px;
      border: 3px solid var(--border);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 12px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
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
      z-index: 20;
    }
    .toast.show { opacity: 1; transform: translateY(0); }
  </style>
</head>
<body>
  <div id="shell" class="shell">
    <aside class="sidebar">
      <div class="sidebar-head">
        <button id="toggle-sidebar" class="icon-btn" type="button" title="Toggle sidebar" aria-label="Toggle sidebar">☰</button>
        <span class="brand">Dashboards</span>
      </div>
      <div class="sidebar-search">
        <input id="search" type="search" placeholder="Search projects..." autofocus>
      </div>
      <nav id="nav" class="nav"></nav>
      <div id="sidebar-count" class="sidebar-foot"></div>
    </aside>
    <main class="main">
      <header id="main-head" class="main-head hidden">
        <div class="main-title">
          <h1 id="main-name"></h1>
          <div id="main-path" class="path"></div>
        </div>
        <div class="main-actions">
          <button id="reload-frame" class="btn" type="button">Reload</button>
          <a id="open-tab" class="btn" href="#" target="_blank" rel="noopener">Open tab</a>
        </div>
      </header>
      <div class="pane">
        <div id="empty" class="empty-state">
          <strong>Select a dashboard</strong>
          <div>Choose a project from the sidebar to load it here.</div>
          <div>Add projects with <code>dashboard-hub add "Name" ~/path/to/project</code></div>
          <div>Projects need a Backlog.md setup (<code>backlog/config.yml</code>).</div>
        </div>
        <div id="loading" class="loading-state hidden">
          <div class="spinner"></div>
          <strong id="loading-label">Starting dashboard...</strong>
        </div>
        <iframe id="frame" class="frame hidden" title="Dashboard" sandbox="allow-same-origin allow-scripts allow-forms allow-popups"></iframe>
      </div>
    </main>
  </div>
  <div id="toast" class="toast"></div>
  <script>
    const shellEl = document.getElementById('shell');
    const searchEl = document.getElementById('search');
    const navEl = document.getElementById('nav');
    const countEl = document.getElementById('sidebar-count');
    const mainHeadEl = document.getElementById('main-head');
    const mainNameEl = document.getElementById('main-name');
    const mainPathEl = document.getElementById('main-path');
    const emptyEl = document.getElementById('empty');
    const loadingEl = document.getElementById('loading');
    const loadingLabelEl = document.getElementById('loading-label');
    const frameEl = document.getElementById('frame');
    const openTabEl = document.getElementById('open-tab');
    const toastEl = document.getElementById('toast');

    let dashboards = [];
    let selectedId = null;
    let currentUrl = null;
    let selecting = false;

    function showToast(message) {
      toastEl.textContent = message;
      toastEl.classList.add('show');
      clearTimeout(showToast._timer);
      showToast._timer = setTimeout(() => toastEl.classList.remove('show'), 2200);
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;');
    }

    function matches(entry, query) {
      if (!query) return true;
      const haystack = [
        entry.id, entry.name, entry.path, entry.description || '',
        entry.running ? 'running' : 'stopped',
      ].join(' ').toLowerCase();
      return haystack.includes(query);
    }

    function setCollapsed(collapsed) {
      shellEl.classList.toggle('collapsed', collapsed);
      localStorage.setItem('dashboard-hub-sidebar-collapsed', collapsed ? '1' : '0');
    }

    function readCollapsed() {
      return localStorage.getItem('dashboard-hub-sidebar-collapsed') === '1';
    }

    function updateUrl(id) {
      const url = new URL(window.location.href);
      if (id) {
        url.searchParams.set('id', id);
      } else {
        url.searchParams.delete('id');
      }
      history.replaceState({}, '', url);
    }

    function showEmpty() {
      emptyEl.classList.remove('hidden');
      loadingEl.classList.add('hidden');
      frameEl.classList.add('hidden');
      mainHeadEl.classList.add('hidden');
      frameEl.removeAttribute('src');
      currentUrl = null;
    }

    function showLoading(label) {
      emptyEl.classList.add('hidden');
      loadingEl.classList.remove('hidden');
      frameEl.classList.add('hidden');
      loadingLabelEl.textContent = label;
    }

    function showFrame(url, entry) {
      emptyEl.classList.add('hidden');
      loadingEl.classList.add('hidden');
      frameEl.classList.remove('hidden');
      mainHeadEl.classList.remove('hidden');
      mainNameEl.textContent = entry.name;
      mainPathEl.textContent = entry.path;
      currentUrl = url;
      openTabEl.href = url;
      if (frameEl.src !== url) {
        frameEl.src = url;
      }
    }

    function renderNav() {
      const query = searchEl.value.trim().toLowerCase();
      const visible = dashboards.filter((entry) => matches(entry, query));
      countEl.textContent = dashboards.length
        ? `${visible.length} of ${dashboards.length}`
        : 'No dashboards configured';

      if (!dashboards.length) {
        navEl.innerHTML = '<div class="empty-state" style="height:auto;padding:16px 8px;">Add one with <code>dashboard-hub add</code></div>';
        return;
      }
      if (!visible.length) {
        navEl.innerHTML = '<div class="empty-state" style="height:auto;padding:16px 8px;">No matches</div>';
        return;
      }

      navEl.innerHTML = visible.map((entry) => `
        <button
          type="button"
          class="nav-item ${entry.id === selectedId ? 'active' : ''} ${selecting && entry.id === selectedId ? 'loading' : ''}"
          data-id="${escapeHtml(entry.id)}"
          title="${escapeHtml(entry.name)}"
        >
          <span class="status-dot ${entry.running ? 'running' : ''}"></span>
          <span class="nav-copy">
            <span class="nav-name">${escapeHtml(entry.name)}</span>
            <span class="nav-meta">${escapeHtml(entry.running ? 'Running' : 'Stopped')} · ${escapeHtml(entry.id)}</span>
          </span>
        </button>
      `).join('');
    }

    async function refresh() {
      const res = await fetch('/api/dashboards');
      dashboards = await res.json();
      renderNav();
    }

    async function selectDashboard(id) {
      if (selecting && id === selectedId) return;
      const entry = dashboards.find((item) => item.id === id);
      if (!entry) return;

      selecting = true;
      selectedId = id;
      updateUrl(id);
      renderNav();
      showLoading(entry.running ? 'Loading backlog...' : 'Starting backlog browser...');

      try {
        const res = await fetch(`/api/dashboards/${encodeURIComponent(id)}/open`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to open dashboard');
        const embedUrl = data.url;
        showFrame(embedUrl, entry);
        if (data.started) showToast('Started ' + entry.name);
        await refresh();
      } catch (error) {
        selectedId = null;
        updateUrl(null);
        showEmpty();
        showToast(error.message);
        await refresh();
      } finally {
        selecting = false;
        renderNav();
      }
    }

    document.getElementById('toggle-sidebar').addEventListener('click', () => {
      setCollapsed(!shellEl.classList.contains('collapsed'));
    });

    navEl.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const button = target.closest('[data-id]');
      if (!(button instanceof HTMLElement)) return;
      selectDashboard(button.dataset.id);
    });

    searchEl.addEventListener('input', renderNav);
    searchEl.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      const query = searchEl.value.trim().toLowerCase();
      const visible = dashboards.filter((entry) => matches(entry, query));
      if (visible.length === 1) {
        selectDashboard(visible[0].id);
      }
    });

    document.getElementById('reload-frame').addEventListener('click', () => {
      if (!currentUrl) return;
      frameEl.src = currentUrl;
    });

    setCollapsed(readCollapsed());
    refresh().then(() => {
      const id = new URL(window.location.href).searchParams.get('id');
      if (id) selectDashboard(id);
    });
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
            resolve_backlog_project(entry.path)
        except FileNotFoundError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        instance = find_instance(entry.id)
        if instance:
            self._send_json(200, {"url": instance.url, "started": False})
            return

        try:
            instance = launch_backlog_browser(entry)
        except RuntimeError as exc:
            self._send_json(500, {"error": str(exc)})
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
