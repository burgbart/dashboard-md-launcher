---
id: TASK-16
title: 'Windows: opening a dashboard flashes a visible console window'
status: Done
assignee: []
created_date: '2026-07-31 17:20'
labels: []
dependencies: []
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On Windows, opening a dashboard from the hub server that isn't already running
pops up a visible terminal/console window instead of staying in the
background like it does on macOS. The dashboard process should keep running
detached from the hub server (same architecture as macOS/Linux — it's an
independent background process, not literally embedded inside the server's
own process), it just shouldn't show a window while doing it.
<!-- SECTION:DESCRIPTION:END -->

## Resolution

<!-- SECTION:DESCRIPTION:BEGIN -->
Root cause: `dashboard_hub/backlog_browser.py` spawned `backlog.cmd` with
`CREATE_NO_WINDOW`, which suppresses a console for that immediate child, but
the child (`node.exe`) re-spawns its own child process (a compiled
`backlog.exe`) internally without any creation flags of its own. Because
node.exe has no console (due to our flag), Windows falls back to its default
`CreateProcess` behavior and auto-allocates a fresh console for that
grandchild — a flag we cannot pass into a spawn we don't control.

Fix: switched from `DETACHED_PROCESS` to `CREATE_NO_WINDOW` for the outer
spawn (they're mutually exclusive; `CREATE_NO_WINDOW` is the stronger of the
two), and added `_suppress_windows_console()` in `backlog_browser.py`, which
runs in a background thread right after spawn, polls the process tree via
`process_tree_pids`, and hides (`ShowWindow(..., SW_HIDE)`) any window owned
by a descendant PID as soon as it appears.

Verified on this machine: launched a real dashboard and polled
`EnumWindows`/`IsWindowVisible` for descendant PIDs over ~4.5s — no visible
window at any point, while the dashboard remained reachable over HTTP the
whole time.
<!-- SECTION:DESCRIPTION:END -->
