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
from .git_remote import get_github_url
from .project_config import compute_short_name, read_project_color, read_project_label, read_project_short_name
from .registry import find_instance, list_instances, terminate_instance, unregister_instance
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
      grid-template-rows: auto auto auto 1fr auto;
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
    .shell.collapsed .sidebar-filters,
    .shell.collapsed .sidebar-foot {
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
    .sidebar-filters {
      padding: 12px;
      border-bottom: 1px solid var(--border);
    }
    .filter-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .filter-chip {
      appearance: none;
      border: 1px solid var(--border);
      background: var(--surface-2);
      color: var(--muted);
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 11px;
      cursor: pointer;
    }
    .filter-chip:hover { border-color: var(--accent); color: var(--heading); }
    .filter-chip.active {
      background: rgba(88, 166, 255, 0.12);
      border-color: rgba(88, 166, 255, 0.35);
      color: var(--accent);
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
    .nav-copy { min-width: 0; overflow: hidden; }
    .nav-name {
      color: var(--heading);
      font-size: 13px;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      display: block;
    }
    .nav-meta {
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-top: 2px;
      display: block;
    }
    .nav-label {
      display: inline-block;
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      margin-top: 3px;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .nav-short {
      display: none;
      font-size: 12px;
      font-weight: 600;
      text-align: center;
      line-height: 1;
    }
    .shell.collapsed .nav-item {
      grid-template-columns: 1fr;
      justify-items: center;
      gap: 6px;
      padding: 10px 8px;
    }
    .shell.collapsed .nav-copy,
    .shell.collapsed .nav-name,
    .shell.collapsed .nav-meta {
      display: none;
    }
    .shell.collapsed .nav-short {
      display: block;
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
    .btn-danger {
      border-color: rgba(248, 81, 73, 0.45);
      color: #f85149;
    }
    .btn-danger:hover {
      border-color: #f85149;
      background: rgba(248, 81, 73, 0.12);
    }
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
      <div id="label-filters" class="sidebar-filters hidden"></div>
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
          <a id="open-github" class="btn hidden" href="#" target="_blank" rel="noopener">GitHub</a>
          <a id="open-cursor" class="btn" href="#">Open in Cursor</a>
          <button id="stop-dashboard" class="btn btn-danger hidden" type="button">Stop</button>
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
    const labelFiltersEl = document.getElementById('label-filters');
    const navEl = document.getElementById('nav');
    const countEl = document.getElementById('sidebar-count');
    const mainHeadEl = document.getElementById('main-head');
    const mainNameEl = document.getElementById('main-name');
    const mainPathEl = document.getElementById('main-path');
    const emptyEl = document.getElementById('empty');
    const loadingEl = document.getElementById('loading');
    const loadingLabelEl = document.getElementById('loading-label');
    const frameEl = document.getElementById('frame');
    const openGithubEl = document.getElementById('open-github');
    const openCursorEl = document.getElementById('open-cursor');
    const openTabEl = document.getElementById('open-tab');
    const stopBtnEl = document.getElementById('stop-dashboard');
    const toastEl = document.getElementById('toast');

    const defaultEmptyHtml = emptyEl.innerHTML;

    let dashboards = [];
    let selectedLabel = null;
    let selectedId = null;
    let currentUrl = null;
    let selecting = false;
    let selectingPollTimer = null;

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

    function matches(entry, query, label) {
      if (label && entry.label !== label) return false;
      if (!query) return true;
      const haystack = [
        entry.id, entry.name, entry.path, entry.description || '',
        entry.label || '', entry.running ? 'running' : 'stopped',
      ].join(' ').toLowerCase();
      return haystack.includes(query);
    }

    function uniqueLabels() {
      return [...new Set(
        dashboards.map((entry) => entry.label).filter(Boolean)
      )].sort((a, b) => a.localeCompare(b));
    }

    function renderLabelFilters() {
      const labels = uniqueLabels();
      if (!labels.length) {
        labelFiltersEl.classList.add('hidden');
        labelFiltersEl.innerHTML = '';
        return;
      }
      labelFiltersEl.classList.remove('hidden');
      const chips = [
        `<button type="button" class="filter-chip ${selectedLabel ? '' : 'active'}" data-label="">All</button>`,
        ...labels.map((label) => `
          <button
            type="button"
            class="filter-chip ${selectedLabel === label ? 'active' : ''}"
            data-label="${escapeHtml(label)}"
          >${escapeHtml(label)}</button>
        `),
      ];
      labelFiltersEl.innerHTML = `<div class="filter-chips">${chips.join('')}</div>`;
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

    function cursorOpenUrl(projectPath) {
      return 'cursor://file' + encodeURI(projectPath);
    }

    function updateHeaderActions(entry) {
      if (entry.githubUrl) {
        openGithubEl.href = entry.githubUrl;
        openGithubEl.classList.remove('hidden');
      } else {
        openGithubEl.classList.add('hidden');
      }
      openCursorEl.href = cursorOpenUrl(entry.path);
    }

    function updateStopButton() {
      const entry = dashboards.find((item) => item.id === selectedId);
      const show = Boolean(entry && entry.running && currentUrl);
      stopBtnEl.classList.toggle('hidden', !show);
    }

    function showEmpty() {
      emptyEl.innerHTML = defaultEmptyHtml;
      emptyEl.classList.remove('hidden');
      loadingEl.classList.add('hidden');
      frameEl.classList.add('hidden');
      mainHeadEl.classList.add('hidden');
      frameEl.removeAttribute('src');
      currentUrl = null;
      updateStopButton();
    }

    function showStopped(entry) {
      emptyEl.innerHTML = `
        <strong>${escapeHtml(entry.name)} stopped</strong>
        <div>Select it again in the sidebar to restart.</div>
      `;
      emptyEl.classList.remove('hidden');
      loadingEl.classList.add('hidden');
      frameEl.classList.add('hidden');
      frameEl.removeAttribute('src');
      currentUrl = null;
      mainHeadEl.classList.remove('hidden');
      mainNameEl.textContent = entry.name;
      mainPathEl.textContent = entry.path;
      updateHeaderActions(entry);
      openTabEl.href = '#';
      updateStopButton();
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
      updateHeaderActions(entry);
      openTabEl.href = url;
      if (frameEl.src !== url) {
        frameEl.src = url;
      }
      updateStopButton();
    }

    function updateDashboardLocal(id, patch) {
      const entry = dashboards.find((item) => item.id === id);
      if (!entry) return;
      Object.assign(entry, patch);
      renderNav();
    }

    function startSelectingPoll() {
      if (selectingPollTimer) return;
      selectingPollTimer = setInterval(refresh, 500);
    }

    function stopSelectingPoll() {
      if (!selectingPollTimer) return;
      clearInterval(selectingPollTimer);
      selectingPollTimer = null;
    }

    function renderNav() {
      const query = searchEl.value.trim().toLowerCase();
      const visible = dashboards.filter((entry) => matches(entry, query, selectedLabel));
      renderLabelFilters();
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

      const existingById = new Map();
      for (const child of [...navEl.children]) {
        if (child.dataset.id) {
          existingById.set(child.dataset.id, child);
        }
      }

      visible.forEach((entry, index) => {
        let item = existingById.get(entry.id);
        const isActive = entry.id === selectedId;
        const isLoading = selecting && entry.id === selectedId;
        const runningClass = entry.running ? 'running' : '';

        if (!item) {
          const classes = ['nav-item'];
          if (isActive) classes.push('active');
          if (isLoading) classes.push('loading');
          item = document.createElement('button');
          item.type = 'button';
          item.className = classes.join(' ');
          item.dataset.id = entry.id;
          item.title = entry.name;
          const labelColor = entry.labelColor || 'var(--accent)';
          item.innerHTML = `
            <span class="status-dot ${runningClass}"></span>
            <span class="nav-copy">
              <span class="nav-name">${escapeHtml(entry.name)}</span>
              ${entry.label ? `<span class="nav-label" style="color: ${escapeHtml(labelColor)}">${escapeHtml(entry.label)}</span>` : ''}
              <span class="nav-meta">${escapeHtml(entry.running ? 'Running' : 'Stopped')} · ${escapeHtml(entry.id)}</span>
            </span>
            <span class="nav-short" style="color: ${escapeHtml(labelColor)}">${escapeHtml(entry.shortName || '')}</span>
          `;
        } else {
          existingById.delete(entry.id);
          item.classList.toggle('active', isActive);
          item.classList.toggle('loading', isLoading);
          item.title = entry.name;
          const labelColor = entry.labelColor || 'var(--accent)';
          const dot = item.querySelector('.status-dot');
          if (dot) dot.classList.toggle('running', entry.running);
          const nameEl = item.querySelector('.nav-name');
          if (nameEl) nameEl.textContent = entry.name;
          const labelEl = item.querySelector('.nav-label');
          if (entry.label) {
            if (labelEl) {
              labelEl.textContent = entry.label;
              labelEl.style.color = labelColor;
            } else {
              const newLabel = document.createElement('span');
              newLabel.className = 'nav-label';
              newLabel.style.color = labelColor;
              newLabel.textContent = entry.label;
              const metaEl = item.querySelector('.nav-meta');
              if (metaEl) metaEl.before(newLabel);
            }
          } else if (labelEl) {
            labelEl.remove();
          }
          const metaEl = item.querySelector('.nav-meta');
          if (metaEl) metaEl.textContent = `${entry.running ? 'Running' : 'Stopped'} · ${entry.id}`;
          const shortEl = item.querySelector('.nav-short');
          if (shortEl) {
            shortEl.textContent = entry.shortName || '';
            shortEl.style.color = labelColor;
          }
        }

        const currentAtIndex = navEl.children[index];
        if (currentAtIndex !== item) {
          navEl.insertBefore(item, currentAtIndex || null);
        }
      });

      for (const item of existingById.values()) {
        item.remove();
      }
    }

    async function refresh() {
      const res = await fetch('/api/dashboards');
      dashboards = await res.json();
      renderNav();
      updateStopButton();
    }

    async function selectDashboard(id) {
      if (selecting && id === selectedId) return;
      const entry = dashboards.find((item) => item.id === id);
      if (!entry) return;

      const needsStart = !entry.running;
      selecting = true;
      selectedId = id;
      updateUrl(id);
      renderNav();
      showLoading(needsStart ? 'Starting backlog browser...' : 'Loading backlog...');
      if (needsStart) {
        startSelectingPoll();
        refresh();
      }

      try {
        const res = await fetch(`/api/dashboards/${encodeURIComponent(id)}/open`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to open dashboard');
        const embedUrl = data.url;
        if (data.started) {
          updateDashboardLocal(id, { running: true, url: embedUrl });
          showToast('Started ' + entry.name);
        }
        showFrame(embedUrl, entry);
        await refresh();
      } catch (error) {
        selectedId = null;
        updateUrl(null);
        showEmpty();
        showToast(error.message);
        await refresh();
      } finally {
        selecting = false;
        stopSelectingPoll();
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
    labelFiltersEl.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const button = target.closest('[data-label]');
      if (!(button instanceof HTMLElement)) return;
      selectedLabel = button.dataset.label || null;
      renderNav();
    });
    searchEl.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      const query = searchEl.value.trim().toLowerCase();
      const visible = dashboards.filter((entry) => matches(entry, query, selectedLabel));
      if (visible.length === 1) {
        selectDashboard(visible[0].id);
      }
    });

    document.getElementById('reload-frame').addEventListener('click', () => {
      if (!currentUrl) return;
      frameEl.src = currentUrl;
    });

    stopBtnEl.addEventListener('click', async () => {
      if (!selectedId || !currentUrl) return;
      const entry = dashboards.find((item) => item.id === selectedId);
      if (!entry || !entry.running) return;

      stopBtnEl.disabled = true;
      try {
        const res = await fetch(`/api/dashboards/${encodeURIComponent(selectedId)}/stop`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to stop dashboard');
        showStopped(entry);
        showToast('Stopped ' + entry.name);
        await refresh();
      } catch (error) {
        showToast(error.message);
        await refresh();
      } finally {
        stopBtnEl.disabled = false;
      }
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
        if parsed.path.startswith(prefix) and parsed.path.endswith("/open"):
            dashboard_id = parsed.path[len(prefix) : -len("/open")]
            self._open_dashboard(dashboard_id)
            return
        if parsed.path.startswith(prefix) and parsed.path.endswith("/stop"):
            dashboard_id = parsed.path[len(prefix) : -len("/stop")]
            self._stop_dashboard(dashboard_id)
            return
        self.send_error(404)

    def _serve_html(self):
        self._send_bytes(200, "text/html; charset=utf-8", HUB_HTML.encode("utf-8"))

    def _serve_dashboards(self):
        config = load_config()
        host = config.hub.host
        instances_by_id = {item.id: item for item in list_instances(host)}
        payload = [
            self._serialize_dashboard(entry, host, instances_by_id.get(entry.id))
            for entry in config.dashboards
        ]
        self._send_bytes(200, "application/json", json.dumps(payload).encode("utf-8"))

    def _serialize_dashboard(
        self,
        entry: DashboardEntry,
        host: str,
        instance=None,
    ) -> dict:
        if instance is None:
            instance = find_instance(entry.id, host)
        label = read_project_label(entry.path)
        label_color = read_project_color(entry.path)
        configured_short = read_project_short_name(entry.path)
        return {
            "id": entry.id,
            "name": entry.name,
            "path": str(entry.path),
            "description": entry.description,
            "running": instance is not None,
            "url": instance.url if instance else None,
            "port": instance.port if instance else None,
            "githubUrl": get_github_url(entry.path),
            "label": label,
            "labelColor": label_color,
            "shortName": compute_short_name(entry.name, configured_short),
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

        instance = find_instance(entry.id, config.hub.host)
        if instance:
            self._send_json(200, {"url": instance.url, "started": False})
            return

        try:
            instance = launch_backlog_browser(entry)
        except RuntimeError as exc:
            self._send_json(500, {"error": str(exc)})
            return
        self._send_json(200, {"url": instance.url, "started": True})

    def _stop_dashboard(self, dashboard_id: str):
        config = load_config()
        entry = find_dashboard(config, dashboard_id)
        if not entry:
            self._send_json(404, {"error": f"Unknown dashboard id: {dashboard_id}"})
            return

        instance = find_instance(entry.id, config.hub.host)
        if not instance:
            self._send_json(404, {"error": "Dashboard is not running"})
            return

        terminate_instance(instance)
        unregister_instance(entry.id)
        self._send_json(200, {"stopped": True})

    def _send_json(self, status: int, payload: dict):
        self._send_bytes(status, "application/json", json.dumps(payload).encode("utf-8"))

    def _send_bytes(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)


def create_server() -> tuple[ThreadingHTTPServer, str]:
    """Bind the hub HTTP server and return it together with its URL."""
    config = load_config()
    host = config.hub.host
    port = config.hub.port
    tool_root = Path(__file__).resolve().parent.parent

    HubHandler.context = HubContext(tool_root=tool_root)
    list_instances(host)

    try:
        server = ThreadingHTTPServer((host, port), HubHandler)
    except OSError as exc:
        print(f"Error: could not bind {host}:{port} ({exc})", file=sys.stderr)
        raise SystemExit(1) from exc

    return server, f"http://{host}:{port}/dashboards/"


def run_server(*, open_browser: bool = True) -> None:
    server, url = create_server()
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
