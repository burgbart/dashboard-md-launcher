# Agent Notes

## Project

`dashboard-md-launcher` is a Python 3.9+ hub for browsing, searching, and launching [Backlog.md](https://github.com/MrLesk/Backlog.md) browser UIs across local projects.

## How to run

```bash
# Add bin/ scripts to PATH or run directly
export PYTHONPATH="$(pwd)${PYTHONPATH:+:$PYTHONPATH}"
python3 -m dashboard_hub server
```

Entry scripts in `bin/`:

- `dashboard-server` — run the hub UI
- `dashboard-hub` — CLI for registering projects and managing browsers
- `dash` — run `backlog browser` in the current project

## Dependencies

- Python 3.9+
- `backlog` CLI available on PATH (install via `npm i -g backlog.md` or `brew install backlog-md`)
- No Python package manager is used; keep the stdlib-only dependency surface unless there is a strong reason to add one.

## Key files

| File | Purpose |
|------|---------|
| `dashboard_hub/__main__.py` | CLI argument parsing and command dispatch |
| `dashboard_hub/server.py` | Hub HTTP server and HTML UI |
| `dashboard_hub/config.py` | User config (`~/.config/dashboard-hub/dashboards.json`) |
| `dashboard_hub/registry.py` | Running instance tracking (`~/.local/share/dashboard-hub/instances.json`) |
| `dashboard_hub/backlog_browser.py` | Spawning `backlog browser` processes |
| `dashboard_hub/project_config.py` | Reading project-level `dashboard-hub/config.yml` metadata |
| `dashboard_hub/git_remote.py` | GitHub URL detection |

## Conventions

- Use `from __future__ import annotations`.
- Prefer `pathlib.Path`, dataclasses, and argparse.
- Keep the hub independent of Backlog.md internals: treat `backlog browser` as an external binary that is spawned and proxied/embedded, not imported.
- Config and state live under `~/.config/dashboard-hub/` and `~/.local/share/dashboard-hub/`.
- Project labels come from `dashboard-hub/config.yml` (or `dashboard-hub.config.yml`, `.dashboard-hub/config.yml`) in each project root.

## Testing

There is no test suite yet. Verify changes manually by:

1. Running `python3 -m dashboard_hub list`
2. Starting the server and opening a dashboard in the browser
3. Checking that start, stop, reload, and search still work

## Design note

Currently the hub does not serve dashboard content itself. Each dashboard is a separate `backlog browser` process that the hub launches and embeds via iframe. Any proposal to run dashboards "under" the hub should either proxy those processes or reimplement the Backlog.md UI.
