---
id: doc-2
title: Desktop version research
type: specification
created_date: '2026-07-31 18:15'
updated_date: '2026-07-31 18:16'
---
# Desktop Version Research (TASK-17 spike)

## Question

Can we ship a lightweight desktop app that runs the dashboards the same as today?
What are the options, and what is the effort/benefit of each? Must stay
cross-platform (macOS, Linux, Windows).

## Current architecture (what a desktop app must wrap)

- `dashboard_hub` is a Python 3.9+ stdlib-only package: an HTTP server
  (`server.py`) serving a single-page HTML UI, plus process management for
  spawned `backlog browser` instances (`backlog_browser.py`, `registry.py`).
- Each dashboard is a separate `backlog browser` process (a Node-based binary)
  on its own port, embedded in the hub UI via an `<iframe>`.
- All state lives in `~/.config/dashboard-hub/` and `~/.local/share/dashboard-hub/`.
- Windows/POSIX differences are already isolated behind `sys.platform` branches.
- Prior decision (doc-1): keep Backlog.md as an external binary; proxy or embed,
  do not reimplement its UI.

Key consequence: any desktop shell only needs to (1) show the hub URL in a
native window and (2) own the Python hub process lifetime. Iframes to
`http://127.0.0.1:<port>` work fine inside any webview, so no UI rewrite is
needed regardless of the option chosen.

## Options

### 1. pywebview wrapper around the existing hub (recommended)

Add a thin `desktop` entry point: start the hub server in a thread, then open a
[pywebview](https://pywebview.flowrl.com/) native window pointing at it.
Package with PyInstaller into a single executable per platform.

- **How it works**: pywebview uses the OS-native webview (WebView2 on Windows,
  WKWebView on macOS, WebKitGTK on Linux). Zero UI changes — the existing hub
  HTML is the app UI. Window close = shutdown hub + stop dashboards (hooks
  already exist in `server.py`/`registry.py`).
- **Effort**: low (days). One new module, one new bin script, PyInstaller spec
  per OS. The only new runtime dependency is `pywebview` itself; everything
  else stays stdlib.
- **Benefits**: smallest delta to the current codebase; single language; keeps
  all cross-platform logic we already built; binary size ~15-30 MB (PyInstaller
  + interpreter, no bundled browser).
- **Drawbacks**: first non-stdlib dependency; PyInstaller packaging per OS is
  fiddly (code signing on macOS/Windows, WebKitGTK dependency on Linux);
  "app feel" is whatever the system webview gives you.
- **Cross-platform**: yes — same three targets we already support. Linux needs
  `webkit2gtk` present (or Qt fallback).

### 2. Tauri (Rust shell + system webview)

A [Tauri](https://v2.tauri.app/) app whose webview loads the hub URL, with the
Python hub bundled as a Tauri *sidecar* binary (PyInstaller-built) that the
Rust shell spawns and kills.

- **Effort**: medium (1-2 weeks). Rust toolchain, Tauri project scaffolding,
  sidecar config, plus still packaging the Python hub via PyInstaller anyway.
- **Benefits**: polished native app: proper installers (.msi, .dmg, .AppImage/
  .deb), auto-updater, tray icon, ~10 MB shell, strong distribution story.
- **Drawbacks**: two toolchains (Rust + Python) and two packaging pipelines;
  the Rust layer adds nothing functionally over option 1 for this app; most of
  the hard part (bundling the Python hub) is identical to option 1.
- **Cross-platform**: excellent, best installer story of all options.

### 3. Electron

Electron shell loading the hub URL, spawning the Python hub as a child process.

- **Effort**: low-medium. Well-trodden path, huge ecosystem, electron-builder
  for installers.
- **Benefits**: mature, predictable, one web engine everywhere (no
  webview-engine differences between OSes).
- **Drawbacks**: bundles Chromium — 150-250 MB installed, high RAM use; cuts
  directly against the "lightweight" requirement; still need to package/spawn
  the Python hub, same as options 1-2.
- **Cross-platform**: excellent.

### 4. Kotlin Compose Multiplatform Desktop

Native Compose shell. Two sub-variants:

- **4a. Compose shell + embedded webview** pointing at the hub URL. Compose
  Desktop has *no official webview* (JetBrains request CMP-8105 still open).
  Community options: [compose-webview-multiplatform](https://github.com/KevinnZou/compose-webview-multiplatform)
  (actively maintained, desktop via JCEF) or KCEF — but **KCEF was archived in
  Nov 2025**, so the JCEF story on desktop currently rests on community
  libraries. JCEF also bundles Chromium (~large artifact again).
- **4b. Fully native Compose UI** reimplementing the hub front-end in Compose,
  talking to the hub HTTP API. Looks great and plays to existing Kotlin
  skills, but duplicates the hub UI (and any future doc-1 proxy work) in a
  second code base; the embedded dashboard iframes still need a webview, so
  4b does not escape 4a's webview problem either.
- **Effort**: medium-high for 4a (JVM app + JCEF integration + jpackage), high
  for 4b (UI rewrite).
- **Benefits**: leverages existing Kotlin/Jetpack Compose expertise; jpackage
  produces .dmg/.msi/.deb; a native shell feels best of all options.
- **Drawbacks**: JVM runtime bundled (~50-80 MB with jlink); webview situation
  on Compose Desktop is immature and community-maintained; still spawns the
  Python hub and backlog binaries, so Kotlin only replaces the shell; 4b forks
  the UI.
- **Cross-platform**: yes, with per-OS jpackage builds (JCEF natives per
  platform add friction).

### 5. PWA / keep the browser (baseline)

Make the hub UI installable as a PWA (manifest + service worker) so users can
"install" it from their browser. Not a real desktop app, but worth recording
as the zero-cost baseline.

- **Effort**: trivial (a manifest and a few lines in `server.py`).
- **Benefits**: no new dependencies, no packaging, works today.
- **Drawbacks**: no control over process lifetime (browser owns it), no single
  "Dashboard.app" to launch, does not satisfy the desktop-app ask by itself.

## Comparison

| Option            | Effort      | App size   | New deps/toolchains        | Keeps current UI | Native feel |
|-------------------|-------------|------------|----------------------------|------------------|-------------|
| 1. pywebview      | Low (days)  | ~15-30 MB  | pywebview + PyInstaller    | Yes              | Medium      |
| 2. Tauri          | Medium      | ~10 MB + hub sidecar | Rust, Tauri, PyInstaller | Yes        | High        |
| 3. Electron       | Low-medium  | 150-250 MB | Node, Electron, PyInstaller| Yes              | Medium      |
| 4a. Compose+JCEF  | Medium-high | ~80-150 MB | JVM, JCEF, jpackage        | Yes (in webview) | High        |
| 4b. Compose native| High        | ~50-80 MB  | JVM, jpackage + UI rewrite | No (rewritten)   | Highest     |
| 5. PWA            | Trivial     | 0          | None                       | Yes              | Low         |

All options still require the `backlog` CLI (Node binary) on the machine or
bundled; that problem is identical everywhere and unchanged from today.

## Recommendation

**Start with option 1 (pywebview + PyInstaller).** It is the only option that
matches "lightweight" while keeping a single-language codebase and reusing all
existing process/port/cross-platform logic. It delivers a real desktop window
in days, not weeks.

- If distribution polish (installers, auto-update, tray) later becomes the
  priority, graduate the same PyInstaller-built hub into a **Tauri** shell
  (option 2) — the hub sidecar work is shared, so option 1 is not a dead end.
- The Kotlin/Compose route (4) is viable but currently buys the least per unit
  of effort: it replaces only the shell, depends on an immature/community
  desktop webview (KCEF archived Nov 2025), and does not remove the Python hub
  or the backlog binary. Revisit if the project ever moves its backend to
  Kotlin.
- Electron fails the "lightweight" requirement outright.

## Suggested next steps (if approved)

1. Add `dashboard_hub/desktop.py`: start hub server on the configured port,
   open a pywebview window, graceful shutdown on window close (stop all running
   dashboards via the existing registry teardown).
2. Add `bin/dashboard-desktop` (+ `.cmd`).
3. Spike PyInstaller packaging on macOS first, then Windows and Linux
   (separate follow-up tasks).
