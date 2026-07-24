# dashboard-md-launcher

Local hub for browsing, searching, and launching `dashboard.md` viewers across projects.

**Repo:** [burgbart/dashboard-md-launcher](https://github.com/burgbart/dashboard-md-launcher)

## Now

| Ticket | Title | Status |
|--------|-------|--------|
| DML-4 | Embed real project dashboards (HTTP URLs) as hub tabs, not only `dashboard.md` | open |

## Backlog

| Ticket | Title | Priority |
|--------|-------|----------|
| DML-1 | LaunchAgent to auto-start `dashboard-server` on login | low |
| DML-2 | Reverse proxy viewer through hub (`/view/:id`) for same-origin embed | low |
| DML-3 | `dashboard-hub edit` command to update config from CLI | low |

## Done

| Ticket | Title | Shipped |
|--------|-------|---------|
| DML-0 | Initial hub + config registry + on-demand launch | v0.1.0 |
| DML-0b | Collapsible sidebar + in-page iframe viewer | v0.2.0 |

## Notes

- Hub: `http://127.0.0.1:17686/dashboards/`
- Config: `~/.config/dashboard-hub/dashboards.json`
- Add tickets to **Now** / **Backlog**; move to **Done** when shipped

### DML-4 — Embed real project dashboards as hub tabs

**Problem:** Selecting a project in the hub only loads the `dashboard.md` markdown viewer. Expected behavior is to see the project's real local dashboard UI in the main pane — e.g. `http://localhost:6420/` for `trmnl-family-plugin` — as one of the tabs/panels.

**Expected:**
- Per-project config supports one or more dashboard targets (markdown ticket board *and/or* HTTP app URL)
- Hub sidebar selection switches the main iframe to the live app URL
- If the app server is not running, launch it (e.g. `trmnl-server`, project-specific command) then embed
- Example: `trmnl-family-plugin` → `http://localhost:6420/`; `mobdevops` → its local UI when applicable

**Likely changes:** extend `dashboards.json` schema (`type`, `url`, `launchCommand`, `port`), hub UI tabs per entry, launch/health-check for HTTP servers instead of only `dashboard_hub viewer`.
