---
id: TASK-18
title: 'Desktop app: pywebview wrapper + PyInstaller executable'
status: To Do
assignee: []
created_date: '2026-07-31 18:23'
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
- [ ] #1 Running the PyInstaller-built executable on macOS opens the hub UI in a native window (no browser), and registered dashboards can be started and embedded exactly as in the browser version
- [ ] #2 Closing the window shuts down the hub and stops all running dashboard processes (verified via the instances registry / no orphan backlog browser processes)
- [ ] #3 The build produces a single-file executable that runs without an installation step
- [ ] #4 bin/dashboard-desktop and bin/dashboard-desktop.cmd run the desktop app from a source checkout on POSIX and Windows respectively
- [ ] #5 README/AGENTS.md document how to build the executable and its limitations (backlog CLI still required, WebKitGTK on Linux, unsigned-binary warnings)
<!-- AC:END -->
