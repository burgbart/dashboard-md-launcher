# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Windows support: `%APPDATA%`/`%LOCALAPPDATA%` config/state dirs, `bin/*.cmd` launchers
- Windows implementations of process liveness, process-tree walking, and
  listening-port lookup (`ctypes` Toolhelp32Snapshot, `netstat -ano`) alongside
  the existing macOS/Linux `ps`/`/proc`/`lsof` code paths
- Cross-platform registry file locking (`msvcrt.locking` on Windows, `fcntl.flock` elsewhere)

### Fixed

- Detached process spawning now uses Windows-compatible `CREATE_NEW_PROCESS_GROUP |
  CREATE_NO_WINDOW` flags instead of the POSIX-only `start_new_session`
- Process termination falls back to `SIGTERM` where `SIGKILL` isn't available (Windows)
- Opening a dashboard on Windows no longer flashes a console window: node.exe
  re-spawns its own child process without inheriting our no-window flag, so a
  background thread now polls for and hides that window right after launch
- `bin/install.ps1` installs `.cmd` shims into `%USERPROFILE%\.local\bin` and
  persists that directory on the User `PATH`, so `dashboard-server`,
  `dashboard-hub`, and `dash` work from any terminal on any platform

## [0.4.0] - 2026-07-24

### Added

- Project labels via `dashboard-hub/config.yml` (`label` field)
- Label badges in the hub sidebar and filter chips to narrow the project list
- `dashboard-hub list` shows labels when configured
- `dashboard-hub doctor [--clean]` reports port collisions and cleans up orphaned browsers

### Fixed

- Top-align the sidebar project list so it sits directly below the label filters
- Add padding above label filter chips so they no longer touch the search box
- Persist unique project ports and verify the spawned process owns its listener
- Stop complete Backlog browser process trees so child listeners are not orphaned

## [0.3.0] - 2026-07-24

### Changed

- **Breaking:** Hub now launches [Backlog.md](https://github.com/MrLesk/Backlog.md) `backlog browser` instead of a custom `dashboard.md` markdown viewer
- Projects must have `backlog/config.yml` (from `backlog init`) to register
- Embedded iframe loads the real Backlog kanban UI
- Removed custom markdown viewer (`viewer.py`)

### Added

- `backlog_browser.py` — spawn and health-check `backlog browser` per project
- Backlog.md initialized for this repository (`backlog/`)

## [0.2.1] - 2026-07-24

### Changed

- Default hub port moved from `8786` to `17686` to reduce clashes with other local tools
- Default viewer port range moved to `17687`–`17799`

## [0.2.0] - 2026-07-23

### Added

- Collapsible sidebar project picker in the hub UI
- In-page dashboard viewing via embedded iframe with `?embed=1` chrome-less viewer mode
- Deep links via `?id=<dashboard-id>` and Enter-to-select when search has one match
- Reload and open-in-tab actions in the main header

### Changed

- Hub layout is now a split sidebar + main pane instead of a card list

## [0.1.0] - 2026-07-23

### Added

- `dashboard-server` hub UI at `/dashboards/` with search and live status
- Config-driven dashboard registry (`dashboard-hub add`, `list`, `remove`, `open`)
- Per-project `dashboard.md` viewer with live reload (`dash`)
- On-demand launch: hub starts a viewer when you open a stopped dashboard
- Runtime registry for tracking active viewer instances and ports
- Zero third-party dependencies (Python 3 standard library only)

[0.4.0]: https://github.com/burgbart/dashboard-md-launcher/releases/tag/v0.4.0
[0.3.0]: https://github.com/burgbart/dashboard-md-launcher/releases/tag/v0.3.0
[0.2.1]: https://github.com/burgbart/dashboard-md-launcher/releases/tag/v0.2.1
[0.2.0]: https://github.com/burgbart/dashboard-md-launcher/releases/tag/v0.2.0
[0.1.0]: https://github.com/burgbart/dashboard-md-launcher/releases/tag/v0.1.0
