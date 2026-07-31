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
- `dashboard-desktop` — run the hub UI in a native webview window (requires `pywebview`)
- `dashboard-hub` — CLI for registering projects and managing browsers
- `dash` — run `backlog browser` in the current project

## Dependencies

- Python 3.9+
- `backlog` CLI available on PATH (install via `npm i -g backlog.md` or `brew install backlog-md`)
- No Python package manager is used; keep the stdlib-only dependency surface unless there is a strong reason to add one.
- Exception: the desktop app (`dashboard_hub/desktop.py`) needs `pywebview`, and building the
  executable needs `pyinstaller`. Both are build/runtime extras for the desktop mode only —
  install them into a `.venv`, never required for the core hub.

## Cross-platform notes

The hub runs on macOS, Linux, and Windows. Platform-specific code is isolated behind
`sys.platform == "win32"` branches rather than separate modules:

- `dashboard_hub/config.py` — config/state dirs use `%APPDATA%`/`%LOCALAPPDATA%` on
  Windows, XDG paths (`~/.config`, `~/.local/share`) elsewhere.
- `dashboard_hub/registry.py` — process liveness, process-tree walking, and
  listening-port lookup each have a Windows implementation (`ctypes`
  Toolhelp32Snapshot, `netstat -ano`) alongside the POSIX one (`ps`, `/proc`,
  `lsof`). File locking uses `msvcrt.locking` on Windows and `fcntl.flock`
  elsewhere. `signal.SIGKILL` doesn't exist on Windows — termination falls
  back to `SIGTERM` (which maps to `TerminateProcess`).
- `dashboard_hub/backlog_browser.py` — detached process spawning uses
  `start_new_session=True` on POSIX and `CREATE_NEW_PROCESS_GROUP |
  DETACHED_PROCESS` on Windows (`start_new_session` isn't supported there).
- `bin/` has both POSIX shell scripts and `.cmd` equivalents
  (`dash.cmd`, `dashboard-hub.cmd`, `dashboard-server.cmd`).
- On Windows, run commands with `python` rather than `python3` — the `python3`
  alias is often an inactive Microsoft Store shim.

## Key files

| File | Purpose |
|------|---------|
| `dashboard_hub/__main__.py` | CLI argument parsing and command dispatch |
| `dashboard_hub/server.py` | Hub HTTP server and HTML UI |
| `dashboard_hub/desktop.py` | Native-window desktop mode (pywebview); starts the hub and tears down dashboards on window close |
| `dashboard_hub/config.py` | User config (`~/.config/dashboard-hub/dashboards.json`) |
| `dashboard_hub/registry.py` | Running instance tracking (`~/.local/share/dashboard-hub/instances.json`) |
| `dashboard_hub/backlog_browser.py` | Spawning `backlog browser` processes |
| `dashboard_hub/project_config.py` | Reading project-level `dashboard-hub/config.yml` metadata |
| `dashboard_hub/git_remote.py` | GitHub URL detection |
| `packaging/dashboard-desktop.spec` | PyInstaller spec for the single-file desktop executable |

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
