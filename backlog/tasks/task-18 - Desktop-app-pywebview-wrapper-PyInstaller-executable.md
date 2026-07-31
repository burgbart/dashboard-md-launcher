---
id: TASK-18
title: 'Desktop app: pywebview wrapper + PyInstaller executable'
status: Done
assignee:
  - '@kimi'
created_date: '2026-07-31 18:23'
updated_date: '2026-07-31 19:48'
labels: []
dependencies:
  - TASK-17
documentation:
  - doc-2
type: feature
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-17 (research in doc-2, option 1). Ship a lightweight desktop app that runs the hub in a native OS webview window instead of a browser tab.

Scope:
1. Add a desktop entry point (e.g. dashboard_hub/desktop.py): start the hub HTTP server in a background thread, open a pywebview window pointing at it, and on window close shut down the hub and stop all running dashboards via the existing registry teardown.
2. Add bin/dashboard-desktop (+ .cmd equivalent) mirroring the existing bin scripts.
3. Add a PyInstaller spec/build that produces a single-file executable (--onefile) per platform — no installation step; the user downloads one file and runs it.

Distribution notes (from research):
- The executable is standalone for the hub itself, but the backlog CLI (Node binary) must still be on PATH or its absence handled gracefully with the existing error message.
- pywebview uses the OS webview: WebView2 (Windows), WKWebView (macOS), WebKitGTK (Linux — document the system package requirement).
- Unsigned binaries trigger Gatekeeper on macOS and SmartScreen on Windows; code signing/notarization is out of scope here but the limitation must be documented.
- Installers (.dmg/.msi) are explicitly out of scope; single-file executable only.

Must stay cross-platform (macOS, Linux, Windows) per existing AGENTS.md conventions: sys.platform branches, both POSIX and .cmd bin scripts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Running the PyInstaller-built executable on macOS opens the hub UI in a native window (no browser), and registered dashboards can be started and embedded exactly as in the browser version
- [x] #2 Closing the window shuts down the hub and stops all running dashboard processes (verified via the instances registry / no orphan backlog browser processes)
- [x] #3 The build produces a single-file executable that runs without an installation step
- [ ] #4 bin/dashboard-desktop and bin/dashboard-desktop.cmd run the desktop app from a source checkout on POSIX and Windows respectively
- [x] #5 README/AGENTS.md document how to build the executable and its limitations (backlog CLI still required, WebKitGTK on Linux, unsigned-binary warnings)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Refactor server.py: extract create_server() (returns server + url) from run_server(); behavior unchanged.
2. Add dashboard_hub/desktop.py: run_desktop() starts the hub server in a daemon thread, opens a pywebview native window at the hub URL, and on window close shuts the server down and terminates/unregisters all running dashboards (registry helpers terminate_instance/unregister_instance/list_instances).
3. Add 'desktop' subcommand in __main__.py mirroring 'server'.
4. Add bin/dashboard-desktop and bin/dashboard-desktop.cmd mirroring the existing scripts.
5. Add packaging/dashboard-desktop.spec (PyInstaller --onefile) plus a small entry script.
6. Test: create .venv, pip install pywebview + pyinstaller; run from source; build onefile executable; verify AC #1-3 on macOS (native window serves hub, start/stop a dashboard, close-window teardown leaves no orphans).
7. Document build + limitations in README.md and AGENTS.md.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation on macOS (arm64, Python 3.12 venv):
- Source run ('python -m dashboard_hub desktop'): native window opened, hub served 200; window close shut the hub down and left registry 0 healthy / 0 stale with no orphaned backlog browser processes (dashboard-hub doctor).
- PyInstaller onefile build: dist/dashboard-desktop, 10 MB single Mach-O arm64 executable, ran directly with no install. Hub served 200; POST /api/dashboards/dashboard-md-launcher/open started backlog browser on 17690 (child of the executable) and the board served 200 — same embed URL as the browser version.
- Window close (AXCloseButton via AppleScript): executable exited, hub down, 17690 process tree gone, doctor clean.
- bin/dashboard-desktop: launched hub via script (200) and exited cleanly on window close. bin/dashboard-desktop.cmd mirrors the proven dashboard-server.cmd but could not be executed here (no Windows machine).
- Regression: 'dashboard_hub server' mode still serves 200 after create_server() refactor; unittest suite 7/7 OK.
- Note: PyInstaller onefile spawns two same-named processes (bootloader + app); harmless, but window-automation must target the one owning the window.

Follow-on work (TASK-19): macOS .app bundle + GUI PATH bugfix completed and verified.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @kimi
created: 2026-07-31 18:33
---
AC #4 Windows half pending: bin/dashboard-desktop.cmd is a verbatim mirror of dashboard-server.cmd (proven on Windows in TASK-15/16) with 'desktop' as the subcommand, but it has not been executed on a Windows machine. Needs a Windows run to fully verify.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Delivered the pywebview desktop app: dashboard_hub/desktop.py (hub in native window, teardown of server + all dashboards on window close), 'desktop' CLI subcommand, bin/dashboard-desktop (+ .cmd), PyInstaller onefile spec, README/AGENTS.md docs. Verified on macOS arm64: source run and onefile executable both served the hub, started a dashboard through the API (board 200, same embed URL as browser), and window close left registry clean with no orphans (doctor). Regression: server mode unaffected, unittest 7/7 OK. AC #4 Windows half not executed (no Windows machine): bin/dashboard-desktop.cmd is a verbatim mirror of the TASK-15/16-proven dashboard-server.cmd; per user decision the task is closed with that caveat recorded in comments. Follow-on: TASK-19 (.app bundle + PATH fix), TASK-17 research in doc-2.
<!-- SECTION:FINAL_SUMMARY:END -->
