---
id: doc-1
title: Run all dashboards under a single server
type: specification
created_date: '2026-07-24 12:34'
---

# Run All Dashboards Under a Single Server

## Current state

`dashboard-server` runs the hub UI on port `17686`. When a project is selected, the hub spawns a separate `backlog browser` process on its own port and embeds it via an iframe. Each dashboard therefore runs as its own HTTP server, with its own port, managed independently.

## Goal

Run every dashboard under the hub server so that users interact with a single origin and port. Start/stop becomes load/unload: a dashboard is either active (served) or inactive (not served), without the user needing to think about separate ports or processes.

## Constraint

`backlog browser` is a compiled binary. Its CLI only exposes `--port`, `--no-open`, `--non-interactive`, and `--help`. It has no static-export mode, no multi-project mode, and no documented API for embedding. Any solution must either proxy the binary or reimplement its UI.

## Options

### 1. Reverse-proxy through the hub (recommended)

Keep spawning `backlog browser` processes, but hide them behind the hub. Dashboards are served under the hub on paths such as:

```text
/dashboard/<id>/          → proxied to the spawned backlog browser
/api/dashboards/<id>/open → starts the process and returns the proxied path
```

The iframe loads `/dashboard/<id>/` instead of `http://127.0.0.1:17691/`.

**Why it matches the goal**
- One address in the browser: `http://dashboards.local:17686/dashboard/<id>/`
- Start/stop is framed as load/unload.
- No change to how Backlog.md behaves.

**Pros**
- Smallest code change.
- Preserves Backlog.md features (drag-and-drop, edit dialogs, search) because the real UI is still running.
- No need to reverse-engineer the binary.

**Cons**
- Child processes and ports still exist under the hood.
- The hub must proxy all traffic, including assets and possibly WebSockets.

**Open question to verify**
Does Backlog.md use absolute URLs or WebSockets? If it does, the proxy must rewrite paths or use per-dashboard subdomains.

### 2. Lazy process pool + proxy

Same proxy idea as option 1, but the hub maintains only a small pool of `backlog browser` processes. A process is assigned to the active dashboard and released back to the pool when another dashboard is loaded. Idle processes are killed after a timeout.

**Pros**
- Fewer total processes/ports when only a few dashboards are used at a time.
- Still uses the real Backlog.md UI.

**Cons**
- More state management.
- A dashboard may need a brief warm start when reassigned.

### 3. Render dashboards inside the hub

Stop using `backlog browser` entirely. The hub reads each project's backlog data directly (`backlog/tasks/`, `backlog/config.yml`) and renders the kanban board itself.

**Pros**
- Truly one server, no child processes, no port management.
- Full control over the UI and URL structure.

**Cons**
- Reimplements part of Backlog.md.
- Risk of feature drift with future Backlog.md versions.
- Must parse Backlog.md's markdown/frontmatter format correctly.

**Variation**
Use the `backlog` CLI only as a data source (e.g. `backlog list`) and render the HTML in the hub.

### 4. Snapshot / cache approach

Spawn `backlog browser` temporarily, fetch its HTML, cache it, then kill the process. The hub serves the cached HTML.

**Pros**
- No long-running child processes.

**Cons**
- The board can go stale.
- Client-side interactivity (drag-and-drop, edits) likely breaks without the live server.
- Not suitable if users need to interact with the board.

## Recommendation

Start with **option 1: reverse-proxy through the hub**. It delivers the single-server user experience with the least risk and the smallest change. It keeps Backlog.md intact and only changes how the hub exposes dashboards.

If, later, we want to eliminate child processes completely, move toward **option 3** (in-process rendering). Treat that as a separate, larger effort.

## Suggested next steps

1. Verify Backlog.md's network behavior behind a path-based proxy (absolute URLs, WebSockets, etc.).
2. Add a proxy route to `dashboard_hub/server.py`.
3. Change `/api/dashboards/<id>/open` to return the proxied path `/dashboard/<id>/`.
4. Update the frontend iframe `src` and remove or relax the `sandbox` attribute if needed.
5. Keep start/stop semantics, but surface them as load/unload in the UI.
